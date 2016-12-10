from collections import OrderedDict
from inspect import Parameter
from warnings import warn
from functools import partial, wraps
from weakref import WeakKeyDictionary
import collections
import inspect
import gc

try:
    from backports.typing import (Callable, Any, Union, Dict, List, TypeVar, Tuple, Set, Sequence,
                                  get_type_hints)
except ImportError:
    from typing import (Callable, Any, Union, Dict, List, TypeVar, Tuple, Set, Sequence,
                        get_type_hints)

try:
    from inspect import unwrap
except ImportError:
    def unwrap(func):
        while hasattr(func, '__wrapped__'):
            func = func.__wrapped__

        return func

__all__ = ('typechecked', 'check_argument_types')

_type_hints_map = WeakKeyDictionary()  # type: Dict[Callable, Dict[str, type]]


def qualified_name(obj) -> str:
    """
    Return the qualified name (e.g. package.module.Type) for the given object.

    Builtins and types from the :mod:`typing` package get special treatment by having the module
    name stripped from the generated name.

    """
    type_ = obj if inspect.isclass(obj) or inspect.isroutine(obj) else type(obj)
    module = type_.__module__
    qualname = type_.__qualname__
    return qualname if module in ('typing', 'builtins') else '{}.{}'.format(module, qualname)


def check_callable(argname: str, value, expected_type, typevars_memo: Dict[Any, type]) -> None:
    if not callable(value):
        raise TypeError('{} must be a callable'.format(argname))

    if isinstance(expected_type.__args__, tuple):
        try:
            signature = inspect.signature(value)
        except (TypeError, ValueError):
            return

        if hasattr(expected_type, '__result__'):
            # Python 3.5
            argument_types = expected_type.__args__
            check_args = argument_types is not Ellipsis
        else:
            # Python 3.6
            argument_types = expected_type.__args__[:-1]
            check_args = argument_types != (Ellipsis,)

        if check_args:
            # The callable must not have keyword-only arguments without defaults
            unfulfilled_kwonlyargs = [
                param.name for param in signature.parameters.values() if
                param.kind == Parameter.KEYWORD_ONLY and param.default == Parameter.empty]
            if unfulfilled_kwonlyargs:
                raise TypeError(
                    'callable passed as {} has mandatory keyword-only arguments in its '
                    'declaration: {}'.format(argname, ', '.join(unfulfilled_kwonlyargs)))

            num_mandatory_args = len([
                param.name for param in signature.parameters.values()
                if param.kind in (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD) and
                param.default is Parameter.empty])
            has_varargs = any(param for param in signature.parameters.values()
                              if param.kind == Parameter.VAR_POSITIONAL)

            if num_mandatory_args > len(argument_types):
                raise TypeError(
                    'callable passed as {} has too many arguments in its declaration; expected {} '
                    'but {} argument(s) declared'.format(argname, len(argument_types),
                                                         num_mandatory_args))
            elif not has_varargs and num_mandatory_args < len(argument_types):
                raise TypeError(
                    'callable passed as {} has too few arguments in its declaration; expected {} '
                    'but {} argument(s) declared'.format(argname, len(argument_types),
                                                         num_mandatory_args))


def check_dict(argname: str, value, expected_type, typevars_memo: Dict[Any, type]) -> None:
    if not isinstance(value, dict):
        raise TypeError('type of {} must be a dict; got {} instead'.
                        format(argname, qualified_name(value)))

    key_type, value_type = getattr(expected_type, '__args__', expected_type.__parameters__)
    for k, v in value.items():
        check_type('keys of {}'.format(argname), k, key_type, typevars_memo)
        check_type('{}[{!r}]'.format(argname, k), v, value_type, typevars_memo)


def check_list(argname: str, value, expected_type, typevars_memo: Dict[Any, type]) -> None:
    if not isinstance(value, list):
        raise TypeError('type of {} must be a list; got {} instead'.
                        format(argname, qualified_name(value)))

    value_type = getattr(expected_type, '__args__', expected_type.__parameters__)[0]
    if value_type:
        for i, v in enumerate(value):
            check_type('{}[{}]'.format(argname, i), v, value_type, typevars_memo)


def check_sequence(argname: str, value, expected_type, typevars_memo: Dict[Any, type]) -> None:
    if not isinstance(value, collections.Sequence):
        raise TypeError('type of {} must be a sequence; got {} instead'.
                        format(argname, qualified_name(value)))

    value_type = getattr(expected_type, '__args__', expected_type.__parameters__)[0]
    if value_type:
        for i, v in enumerate(value):
            check_type('{}[{}]'.format(argname, i), v, value_type, typevars_memo)


def check_set(argname: str, value, expected_type, typevars_memo: Dict[Any, type]) -> None:
    if not isinstance(value, collections.Set):
        raise TypeError('type of {} must be a set; got {} instead'.
                        format(argname, qualified_name(value)))

    value_type = getattr(expected_type, '__args__', expected_type.__parameters__)[0]
    if value_type:
        for v in value:
            check_type('elements of {}'.format(argname), v, value_type, typevars_memo)


def check_tuple(argname: str, value, expected_type, typevars_memo: Dict[Any, type]) -> None:
    if not isinstance(value, tuple):
        raise TypeError('type of {} must be a tuple; got {} instead'.
                        format(argname, qualified_name(value)))

    if hasattr(expected_type, '__tuple_use_ellipsis__'):
        # Python 3.5
        use_ellipsis = expected_type.__tuple_use_ellipsis__
        tuple_params = expected_type.__tuple_params__
    else:
        # Python 3.6+
        use_ellipsis = expected_type.__args__[-1] is Ellipsis
        tuple_params = expected_type.__args__[:-1 if use_ellipsis else None]

    if use_ellipsis:
        element_type = tuple_params[0]
        for i, element in enumerate(value):
            check_type('{}[{}]'.format(argname, i), element, element_type, typevars_memo)
    else:
        if len(value) != len(tuple_params):
            raise TypeError('{} has wrong number of elements (expected {}, got {} instead)'
                            .format(argname, len(tuple_params), len(value)))

        for i, (element, element_type) in enumerate(zip(value, tuple_params)):
            check_type('{}[{}]'.format(argname, i), element, element_type, typevars_memo)


def check_union(argname: str, value, expected_type, typevars_memo: Dict[Any, type]) -> None:
    if hasattr(expected_type, '__union_params__'):
        # Python 3.5
        union_params = expected_type.__union_params__
    else:
        # Python 3.6+
        union_params = expected_type.__args__

    for type_ in union_params:
        try:
            check_type(argname, value, type_, typevars_memo)
            return
        except TypeError:
            pass

    typelist = ', '.join(t.__name__ for t in union_params)
    raise TypeError('type of {} must be one of ({}); got {} instead'.
                    format(argname, typelist, qualified_name(value)))


def check_typevar(argname: str, value, typevar: TypeVar,
                  typevars_memo: Dict[Any, type]) -> None:
    bound_type = typevars_memo.get(typevar)
    value_type = type(value)
    if bound_type is not None:
        # The type variable has been bound to a concrete type -- check that the value matches
        # the bound type according to the type variable's rules
        if typevar.__covariant__:
            if not isinstance(value, bound_type):
                raise TypeError(
                    '{} must be an instance of {}; got {} instead'.
                    format(argname, qualified_name(bound_type), qualified_name(value_type)))
        elif typevar.__contravariant__:
            if not issubclass(bound_type, value_type):
                raise TypeError(
                    'type of {} must be {} or one of its superclasses; got {} instead'.
                    format(argname, qualified_name(bound_type), qualified_name(value_type)))
        else:  # invariant
            if value_type is not bound_type:
                raise TypeError(
                    'type of {} must be exactly {}; got {} instead'.
                    format(argname, qualified_name(bound_type), qualified_name(value_type)))
    else:
        # The type variable hasn't been bound yet -- check that the given value matches the
        # constraints of the type variable, if any
        if typevar.__constraints__ and value_type not in typevar.__constraints__:
            typelist = ', '.join(t.__name__ for t in typevar.__constraints__
                                 if t is not object)
            raise TypeError('type of {} must be one of ({}); got {} instead'.
                            format(argname, typelist, qualified_name(value_type)))
        elif typevar.__bound__:
            if not isinstance(value, typevar.__bound__):
                raise TypeError(
                    '{} must be an instance of {}; got {} instead'.
                    format(argname, qualified_name(typevar.__bound__),
                           qualified_name(value_type)))

        # Bind the type variable to a concrete type
        typevars_memo[typevar] = value_type


# Equality checks are applied to these
origin_type_checkers = {
    Dict: check_dict,
    List: check_list,
    Sequence: check_sequence,
    Set: check_set,
    Union: check_union
}

# issubclass() checks are applied to these
subclass_type_checkers = {
    Callable: check_callable,
    Tuple: check_tuple
}
if hasattr(Union, '__union_set_params__'):
    subclass_type_checkers[Union] = check_union


def check_type(argname: str, value, expected_type, typevars_memo: Dict[Any, type]) -> None:
    """
    Ensure that ``value`` matches ``expected_type``.

    The types from the :mod:`typing` module do not support :func:`isinstance` or :func:`issubclass`
    so a number of type specific checks are required. This function knows which checker to call
    for which type.

    :param argname: name of the argument to check; used for error messages
    :param value: value to be checked against ``expected_type``
    :param expected_type: a class or generic type instance
    :param typevars_memo: dictionary of type variables and their bound types

    """
    if expected_type is Any:
        return
    elif expected_type is None:
        # Only happens on < 3.6
        expected_type = type(None)

    origin_type = getattr(expected_type, '__origin__', None)
    if origin_type is not None:
        checker_func = origin_type_checkers.get(origin_type)
        if checker_func:
            checker_func(argname, value, expected_type, typevars_memo)
            return

    if isinstance(expected_type, TypeVar):
        check_typevar(argname, value, expected_type, typevars_memo)
        return

    for type_, checker_func in subclass_type_checkers.items():
        if issubclass(expected_type, type_):
            checker_func(argname, value, expected_type, typevars_memo)
            return

    if not isinstance(value, expected_type):
        raise TypeError(
            'type of {} must be {}; got {} instead'.
            format(argname, qualified_name(expected_type), qualified_name(type(value))))


def check_argument_types(func: Callable = None, args: tuple = None, kwargs: Dict[str, Any] = None,
                         typevars_memo: Dict[Any, type] = None) -> bool:
    """
    Check that the argument values match the annotated types.

    Unless both ``args`` and ``kwargs`` are provided, the information will be retrieved from
    the previous stack frame (ie. from the function that called this).

    :param func: the callable to check the arguments against
    :param args: positional arguments the callable was called with
    :param kwargs: keyword arguments the callable was called with
    :param typevars_memo: dictionary of type variables and their bound types (for internal use)
    :return: ``True``
    :raises TypeError: if there is an argument type mismatch

    """
    frame = inspect.currentframe().f_back
    if func:
        func = unwrap(func)
    else:
        # No callable provided, so fish it out of the garbage collector
        for obj in gc.get_referrers(frame.f_code):
            if inspect.isfunction(obj):
                func = obj
                break
        else:  # pragma: no cover
            return True

    signature = inspect.signature(func)
    type_hints = _type_hints_map.get(func)
    if type_hints is None:
        hints = get_type_hints(func)
        type_hints = _type_hints_map[func] = OrderedDict(
            (name, hints[name]) for name in tuple(signature.parameters) + ('return',)
            if name in hints)

        # If an argument has a default value, its type should be accepted as well
        for param in signature.parameters.values():
            if param.default is not Parameter.empty and param.name in hints:
                type_hints[param.name] = Union[hints[param.name], type(param.default)]

    if args is None or kwargs is None:
        argvalues = frame.f_locals
    elif isinstance(args, tuple) and isinstance(kwargs, dict):
        argvalues = signature.bind(*args, **kwargs).arguments
    else:
        raise TypeError('args must be a tuple and kwargs must be a dict')

    if typevars_memo is None:
        typevars_memo = {}

    func_name = qualified_name(func)
    for argname, expected_type in type_hints.items():
        if argname != 'return' and argname in argvalues:
            value = argvalues[argname]
            argname = 'argument {}'.format(argname, func_name)
            check_type(argname, value, expected_type, typevars_memo)

    return True


def typechecked(func: Callable = None, *, always: bool = False):
    """
    Perform runtime type checking on the arguments that are passed to the wrapped function.

    The return value is also checked against the return annotation if any.

    If the ``__debug__`` global variable is set to ``False``, no wrapping and therefore no type
    checking is done, unless ``always`` is ``True``.

    :param func: the function to enable type checking for
    :param always: ``True`` to enable type checks even in optimized mode

    """
    if not __debug__ and not always:  # pragma: no cover
        return func

    if func is None:
        return partial(typechecked, always=always)

    func_name = qualified_name(func)
    annotations = getattr(func, '__annotations__', {})
    if not annotations:
        warn('no type annotations present -- not typechecking {}'.format(func_name))
        return func

    def check_return_value_type(retval, typevars_memo: Dict[Any, type]):
        type_hints = _type_hints_map[func]
        if 'return' in type_hints:
            check_type('the return value of {}()'.format(func_name), retval, type_hints['return'],
                       typevars_memo)

    @wraps(func)
    def wrapper(*args, **kwargs):
        typevars_memo = {}  # type: Dict[TypeVar, type]
        check_argument_types(func, args, kwargs, typevars_memo)
        retval = func(*args, **kwargs)
        check_return_value_type(retval, typevars_memo)
        return retval

    return wrapper
