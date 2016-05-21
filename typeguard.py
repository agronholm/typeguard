from typing import Callable, Any, Union, Dict, List, TypeVar, Tuple, Set, Sequence, get_type_hints
from collections import OrderedDict
from warnings import warn
from functools import partial, wraps
from weakref import WeakKeyDictionary
import collections
import inspect
import gc

__all__ = ('typechecked', 'check_argument_types')

_type_hints_map = WeakKeyDictionary()  # type: Dict[Callable, Dict[str, type]]


def qualified_name(obj) -> str:
    """
    Return the qualified name (e.g. package.module.Type) for the given object.

    Builtins and types from the :mod:`typing` package get special treatment by having the module
    name stripped from the generated name.

    On Python 3.2, generated names may be less accurate due to the absence of the ``__qualname__``
    attribute.

    """
    try:
        module = obj.__module__
        qualname = getattr(obj, '__qualname__', obj.__name__)
    except AttributeError:
        type_ = type(obj)
        module = type_.__module__
        qualname = getattr(type_, '__qualname__', type_.__name__)

    return qualname if module in ('typing', 'builtins') else '{}.{}'.format(module, qualname)


def check_callable(argname: str, value, expected_type, typevars_memo: Dict[TypeVar, type]) -> None:
    if not callable(value):
        raise TypeError('{} must be a callable'.format(argname))

    if isinstance(expected_type.__args__, tuple):
        try:
            spec = inspect.getfullargspec(value)
        except (TypeError, ValueError):
            return

        # The callable must not have keyword-only arguments without defaults
        unfulfilled_kwonlyargs = [arg for arg in spec.kwonlyargs if
                                  not spec.kwonlydefaults or arg not in spec.kwonlydefaults]
        if unfulfilled_kwonlyargs:
            raise TypeError(
                'callable passed as {} has mandatory keyword-only arguments in its '
                'declaration: {}'.format(argname, ', '.join(unfulfilled_kwonlyargs)))

        mandatory_args = set(spec.args)
        if spec.defaults:
            mandatory_args -= set(spec.args[-len(spec.defaults):])
        if isinstance(value, partial):
            # Don't count the arguments passed in through partial()
            mandatory_args -= set(spec.args[:len(value.args)])
            mandatory_args -= set(value.keywords or ())
            if inspect.isclass(value.func):
                # Don't count the "self" argument for class constructors
                mandatory_args -= {spec.args[0]}
        elif inspect.ismethod(value) or inspect.isclass(value):
            # Don't count the "self" argument for bound methods or class constructors
            mandatory_args -= {spec.args[0]}

        if len(mandatory_args) > len(expected_type.__args__):
            raise TypeError(
                'callable passed as {} has too many arguments in its declaration; expected {} '
                'but {} argument(s) declared'.format(argname, len(expected_type.__args__),
                                                     len(mandatory_args)))
        elif not spec.varargs and len(mandatory_args) < len(expected_type.__args__):
            raise TypeError(
                'callable passed as {} has too few arguments in its declaration; expected {} '
                'but {} argument(s) declared'.format(argname, len(expected_type.__args__),
                                                     len(mandatory_args)))


def check_dict(argname: str, value, expected_type, typevars_memo: Dict[TypeVar, type]) -> None:
    if not isinstance(value, dict):
        raise TypeError('type of {} must be a dict; got {} instead'.
                        format(argname, qualified_name(value)))

    key_type, value_type = expected_type.__parameters__
    for k, v in value.items():
        check_type('keys of {}'.format(argname), k, key_type, typevars_memo)
        check_type('{}[{!r}]'.format(argname, k), v, value_type, typevars_memo)


def check_list(argname: str, value, expected_type, typevars_memo: Dict[TypeVar, type]) -> None:
    if not isinstance(value, list):
        raise TypeError('type of {} must be a list; got {} instead'.
                        format(argname, qualified_name(value)))
    if expected_type.__parameters__:
        value_type = expected_type.__parameters__[0]
        for i, v in enumerate(value):
            check_type('{}[{}]'.format(argname, i), v, value_type, typevars_memo)


def check_sequence(argname: str, value, expected_type, typevars_memo: Dict[TypeVar, type]) -> None:
    if not isinstance(value, collections.Sequence):
        raise TypeError('type of {} must be a sequence; got {} instead'.
                        format(argname, qualified_name(value)))
    if expected_type.__parameters__:
        value_type = expected_type.__parameters__[0]
        for i, v in enumerate(value):
            check_type('{}[{}]'.format(argname, i), v, value_type, typevars_memo)


def check_set(argname: str, value, expected_type, typevars_memo: Dict[TypeVar, type]) -> None:
    if not isinstance(value, collections.Set):
        raise TypeError('type of {} must be a set; got {} instead'.
                        format(argname, qualified_name(value)))
    if expected_type.__parameters__:
        value_type = expected_type.__parameters__[0]
        for v in value:
            check_type('elements of {}'.format(argname), v, value_type, typevars_memo)


def check_tuple(argname: str, value, expected_type, typevars_memo: Dict[TypeVar, type]) -> None:
    if not isinstance(value, tuple):
        raise TypeError('type of {} must be a tuple; got {} instead'.
                        format(argname, qualified_name(value)))
    if len(value) != len(expected_type.__tuple_params__):
        raise TypeError('{} has wrong number of elements (expected {}, got {} instead)'
                        .format(argname, len(expected_type.__tuple_params__), len(value)))
    for i, (element, expected_type) in enumerate(zip(value, expected_type.__tuple_params__)):
        check_type('{}[{}]'.format(argname, i), element, expected_type, typevars_memo)


def check_union(argname: str, value, expected_type, typevars_memo: Dict[TypeVar, type]) -> None:
    for type_ in expected_type.__union_params__:
        try:
            check_type(argname, value, type_, typevars_memo)
            return
        except TypeError:
            pass

    typelist = ', '.join(t.__name__ for t in expected_type.__union_params__)
    raise TypeError('type of {} must be one of ({}); got {} instead'.
                    format(argname, typelist, qualified_name(value)))


def check_typevar(argname: str, value, typevar: TypeVar,
                  typevars_memo: Dict[TypeVar, type]) -> None:
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
    Set: check_set
}

# issubclass() checks are applied to these
subclass_type_checkers = {
    Callable: check_callable,
    Tuple: check_tuple,
    Union: check_union
}


def check_type(argname: str, value, expected_type, typevars_memo: Dict[TypeVar, type]) -> None:
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

    origin_type = getattr(expected_type, '__origin__', None)
    if origin_type is not None:
        checker_func = origin_type_checkers.get(origin_type)
        if checker_func:
            checker_func(argname, value, expected_type, typevars_memo)
            return

    for type_, checker_func in subclass_type_checkers.items():
        if issubclass(expected_type, type_):
            checker_func(argname, value, expected_type, typevars_memo)
            return

    if isinstance(expected_type, TypeVar):
        check_typevar(argname, value, expected_type, typevars_memo)
    elif not isinstance(value, expected_type):
        raise TypeError(
            'type of {} must be {}; got {} instead'.
            format(argname, qualified_name(expected_type), qualified_name(type(value))))


def check_argument_types(func: Callable = None, args: tuple = None, kwargs: Dict[str, Any] = None,
                         typevars_memo: Dict[TypeVar, type] = None) -> bool:
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
        # Unwrap the function
        while hasattr(func, '__wrapped__'):
            func = func.__wrapped__
    else:
        # No callable provided, so fish it out of the garbage collector
        for obj in gc.get_referrers(frame.f_code):
            if inspect.isfunction(obj):
                func = obj
                break
        else:
            return True

    spec = inspect.getfullargspec(func)
    type_hints = _type_hints_map.get(func)
    if type_hints is None:
        hints = get_type_hints(func)
        type_hints = _type_hints_map[func] = OrderedDict(
            (arg, hints[arg]) for arg in spec.args + ['return'] if arg in hints)

        # If an argument has a default value, its type should be accepted as well
        if spec.defaults:
            for argname, default_value in zip(reversed(spec.args), reversed(spec.defaults)):
                if argname in hints:
                    type_hints[argname] = Union[hints[argname], type(default_value)]

    if args is None or kwargs is None:
        argvalues = frame.f_locals
    elif isinstance(args, tuple) and isinstance(kwargs, dict):
        argvalues = kwargs.copy()
        pos_values = dict(zip(spec.args, args))
        argvalues.update(pos_values)
    else:
        raise TypeError('args must be a tuple and kwargs must be a dict')

    if typevars_memo is None:
        typevars_memo = {}

    func_name = qualified_name(func)
    for argname, expected_type in type_hints.items():
        if argname != 'return':
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

    def check_return_value_type(retval, typevars_memo: Dict[TypeVar, type]):
        type_hints = _type_hints_map[func]
        expected_type = type_hints.get('return')
        if expected_type is not None:
            check_type('the return value of {}()'.format(func_name), retval, expected_type,
                       typevars_memo)

    @wraps(func)
    def wrapper(*args, **kwargs):
        typevars_memo = {}  # type: Dict[TypeVar, type]
        check_argument_types(func, args, kwargs, typevars_memo)
        retval = func(*args, **kwargs)
        check_return_value_type(retval, typevars_memo)
        return retval

    return wrapper
