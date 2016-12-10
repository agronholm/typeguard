from collections import OrderedDict
from inspect import Parameter, isclass
from warnings import warn
from functools import partial, wraps
from weakref import WeakKeyDictionary
import collections
import inspect
import gc

try:
    from backports.typing import (Callable, Any, Union, Dict, List, TypeVar, Tuple, Set, Sequence,
                                  get_type_hints, Type)
except ImportError:
    from typing import (Callable, Any, Union, Dict, List, TypeVar, Tuple, Set, Sequence,
                        get_type_hints)

    try:
        from typing import Type
    except ImportError:
        Type = None

try:
    from inspect import unwrap
except ImportError:
    def unwrap(func):
        while hasattr(func, '__wrapped__'):
            func = func.__wrapped__

        return func

__all__ = ('typechecked', 'check_argument_types')


class _CallMemo:
    type_hints_map = WeakKeyDictionary()  # type: Dict[Callable, Dict[str, type]]

    def __init__(self, frame=None, func=None, args: tuple = None, kwargs: Dict[str, Any] = None):
        if func is None:
            # No callable provided, so fish it out of the garbage collector
            assert frame, 'frame must be specified if func is None'
            for obj in gc.get_referrers(frame.f_code):
                if inspect.isfunction(obj):
                    func = obj
                    break

        self.func_name = qualified_name(func)
        self.signature = inspect.signature(func)
        self.typevars = {}  # type: Dict[Any, type]

        if args is not None and kwargs is not None:
            self.arguments = self.signature.bind(*args, **kwargs).arguments
        else:
            assert frame, 'frame must be specified if args or kwargs is None'
            self.arguments = frame.f_locals

        self.type_hints = self.type_hints_map.get(func)
        if self.type_hints is None:
            hints = get_type_hints(func)
            self.type_hints = self.type_hints_map[func] = OrderedDict(
                (name, hints[name]) for name in tuple(self.signature.parameters) + ('return',)
                if name in hints)

            # If an argument has a default value, its type should be accepted as well
            for param in self.signature.parameters.values():
                if param.default is not Parameter.empty and param.name in hints:
                    self.type_hints[param.name] = Union[hints[param.name], type(param.default)]


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


def check_callable(argname: str, value, expected_type, memo: _CallMemo) -> None:
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


def check_dict(argname: str, value, expected_type, memo: _CallMemo) -> None:
    if not isinstance(value, dict):
        raise TypeError('type of {} must be a dict; got {} instead'.
                        format(argname, qualified_name(value)))

    key_type, value_type = getattr(expected_type, '__args__', expected_type.__parameters__)
    for k, v in value.items():
        check_type('keys of {}'.format(argname), k, key_type, memo)
        check_type('{}[{!r}]'.format(argname, k), v, value_type, memo)


def check_list(argname: str, value, expected_type, memo: _CallMemo) -> None:
    if not isinstance(value, list):
        raise TypeError('type of {} must be a list; got {} instead'.
                        format(argname, qualified_name(value)))

    value_type = getattr(expected_type, '__args__', expected_type.__parameters__)[0]
    if value_type:
        for i, v in enumerate(value):
            check_type('{}[{}]'.format(argname, i), v, value_type, memo)


def check_sequence(argname: str, value, expected_type, memo: _CallMemo) -> None:
    if not isinstance(value, collections.Sequence):
        raise TypeError('type of {} must be a sequence; got {} instead'.
                        format(argname, qualified_name(value)))

    value_type = getattr(expected_type, '__args__', expected_type.__parameters__)[0]
    if value_type:
        for i, v in enumerate(value):
            check_type('{}[{}]'.format(argname, i), v, value_type, memo)


def check_set(argname: str, value, expected_type, memo: _CallMemo) -> None:
    if not isinstance(value, collections.Set):
        raise TypeError('type of {} must be a set; got {} instead'.
                        format(argname, qualified_name(value)))

    value_type = getattr(expected_type, '__args__', expected_type.__parameters__)[0]
    if value_type:
        for v in value:
            check_type('elements of {}'.format(argname), v, value_type, memo)


def check_tuple(argname: str, value, expected_type, memo: _CallMemo) -> None:
    # Specialized check for NamedTuples
    if hasattr(expected_type, '_field_types'):
        if not isinstance(value, expected_type):
            raise TypeError('type of {} must be a named tuple of type {}; got {} instead'.
                            format(argname, qualified_name(expected_type), qualified_name(value)))

        for name, field_type in expected_type._field_types.items():
            check_type('{}.{}'.format(argname, name), getattr(value, name), field_type, memo)

        return
    elif not isinstance(value, tuple):
        raise TypeError('type of {} must be a tuple; got {} instead'.
                        format(argname, qualified_name(value)))

    if getattr(expected_type, '__tuple_params__', None):
        # Python 3.5
        use_ellipsis = expected_type.__tuple_use_ellipsis__
        tuple_params = expected_type.__tuple_params__
    elif getattr(expected_type, '__args__', None):
        # Python 3.6+
        use_ellipsis = expected_type.__args__[-1] is Ellipsis
        tuple_params = expected_type.__args__[:-1 if use_ellipsis else None]
    else:
        # Unparametrized Tuple or plain tuple
        return

    if use_ellipsis:
        element_type = tuple_params[0]
        for i, element in enumerate(value):
            check_type('{}[{}]'.format(argname, i), element, element_type, memo)
    else:
        if len(value) != len(tuple_params):
            raise TypeError('{} has wrong number of elements (expected {}, got {} instead)'
                            .format(argname, len(tuple_params), len(value)))

        for i, (element, element_type) in enumerate(zip(value, tuple_params)):
            check_type('{}[{}]'.format(argname, i), element, element_type, memo)


def check_union(argname: str, value, expected_type, memo: _CallMemo) -> None:
    if hasattr(expected_type, '__union_params__'):
        # Python 3.5
        union_params = expected_type.__union_params__
    else:
        # Python 3.6+
        union_params = expected_type.__args__

    for type_ in union_params:
        try:
            check_type(argname, value, type_, memo)
            return
        except TypeError:
            pass

    typelist = ', '.join(t.__name__ for t in union_params)
    raise TypeError('type of {} must be one of ({}); got {} instead'.
                    format(argname, typelist, qualified_name(value)))


def check_class(argname: str, value, expected_type, typevars_memo: Dict[Any, type]) -> None:
    if not isclass(value):
        raise TypeError('{} must be a type; got {} instead'.format(argname, qualified_name(value)))

    expected_class = expected_type.__args__[0] if expected_type.__args__ else None
    if expected_class and not issubclass(value, expected_class):
        raise TypeError('{} must be a subclass of {}; got {} instead'.format(
            argname, qualified_name(expected_class), qualified_name(value)))


def check_typevar(argname: str, value, typevar: TypeVar, memo: _CallMemo) -> None:
    bound_type = memo.typevars.get(typevar)
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
        memo.typevars[typevar] = value_type


# Equality checks are applied to these
origin_type_checkers = {
    Dict: check_dict,
    List: check_list,
    Sequence: check_sequence,
    Set: check_set,
    Union: check_union
}
_subclass_check_unions = hasattr(Union, '__union_set_params__')
if Type is not None:
    origin_type_checkers[Type] = check_class


def check_type(argname: str, value, expected_type, memo: _CallMemo) -> None:
    """
    Ensure that ``value`` matches ``expected_type``.

    The types from the :mod:`typing` module do not support :func:`isinstance` or :func:`issubclass`
    so a number of type specific checks are required. This function knows which checker to call
    for which type.

    :param argname: name of the argument to check; used for error messages
    :param value: value to be checked against ``expected_type``
    :param expected_type: a class or generic type instance

    """
    if expected_type is Any:
        return

    if expected_type is None:
        # Only happens on < 3.6
        expected_type = type(None)

    if isclass(expected_type):
        origin_type = getattr(expected_type, '__origin__', None)
        if origin_type is not None:
            checker_func = origin_type_checkers.get(origin_type)
            if checker_func:
                checker_func(argname, value, expected_type, memo)
                return

        if issubclass(expected_type, Tuple):
            check_tuple(argname, value, expected_type, memo)
        elif issubclass(expected_type, Callable) and hasattr(expected_type, '__args__'):
            check_callable(argname, value, expected_type, memo)
        elif _subclass_check_unions and issubclass(expected_type, Union):
            check_union(argname, value, expected_type, memo)
        elif isinstance(expected_type, TypeVar):
            check_typevar(argname, value, expected_type, memo)
        else:
            expected_type = getattr(expected_type, '__extra__', expected_type)
            if not isinstance(value, expected_type):
                raise TypeError(
                    'type of {} must be {}; got {} instead'.
                    format(argname, qualified_name(expected_type), qualified_name(type(value))))
    elif isinstance(expected_type, TypeVar):
        # Only happens on < 3.6
        check_typevar(argname, value, expected_type, memo)
    elif getattr(expected_type, '__origin__', None) is Union:
        # Only happens on 3.6+
        check_union(argname, value, expected_type, memo)


def check_return_type(retval, memo: _CallMemo) -> bool:
    if 'return' in memo.type_hints:
        check_type('the return value of {}()'.format(memo.func_name), retval,
                   memo.type_hints['return'], memo)

    return True


def check_argument_types(memo: _CallMemo = None) -> bool:
    """
    Check that the argument values match the annotated types.

    Unless both ``args`` and ``kwargs`` are provided, the information will be retrieved from
    the previous stack frame (ie. from the function that called this).

    :param func: the callable to check the arguments against
    :return: ``True``
    :raises TypeError: if there is an argument type mismatch

    """
    if memo is None:
        frame = inspect.currentframe().f_back
        memo = _CallMemo(frame)

    for argname, expected_type in memo.type_hints.items():
        if argname != 'return' and argname in memo.arguments:
            value = memo.arguments[argname]
            description = 'argument {}'.format(argname, memo.func_name)
            check_type(description, value, expected_type, memo)

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

    if not getattr(func, '__annotations__', None):
        warn('no type annotations present -- not typechecking {}'.format(qualified_name(func)))
        return func

    @wraps(func)
    def wrapper(*args, **kwargs):
        memo = _CallMemo(func=func, args=args, kwargs=kwargs)
        check_argument_types(memo)
        retval = func(*args, **kwargs)
        check_return_type(retval, memo)
        return retval

    return wrapper
