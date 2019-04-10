__all__ = ('typechecked', 'check_argument_types', 'check_type', 'TypeWarning', 'TypeChecker')

import collections.abc
import gc
import inspect
import sys
import threading
from collections import OrderedDict
from functools import wraps, partial
from inspect import Parameter, isclass, isfunction
from io import TextIOBase, RawIOBase, IOBase, BufferedIOBase
from traceback import extract_stack, print_stack
from types import CodeType, FunctionType  # noqa
from typing import (
    Callable, Any, Union, Dict, List, TypeVar, Tuple, Set, Sequence,
    get_type_hints, TextIO, Optional, IO, BinaryIO)
from warnings import warn
from weakref import WeakKeyDictionary, WeakValueDictionary

try:
    from typing import Type
except ImportError:
    Type = None

_type_hints_map = WeakKeyDictionary()  # type: Dict[FunctionType, Dict[str, Any]]
_functions_map = WeakValueDictionary()  # type: Dict[CodeType, FunctionType]


class _CallMemo:
    __slots__ = ('func', 'func_name', 'signature', 'typevars', 'arguments', 'type_hints')

    def __init__(self, func: Callable, frame=None, args: tuple = None,
                 kwargs: Dict[str, Any] = None):
        self.func = func
        self.func_name = function_name(func)
        self.signature = inspect.signature(func)
        self.typevars = {}  # type: Dict[Any, type]

        if args is not None and kwargs is not None:
            self.arguments = self.signature.bind(*args, **kwargs).arguments
        else:
            assert frame, 'frame must be specified if args or kwargs is None'
            self.arguments = frame.f_locals.copy()

        self.type_hints = _type_hints_map.get(func)
        if self.type_hints is None:
            hints = get_type_hints(func)
            self.type_hints = OrderedDict()
            for name, parameter in self.signature.parameters.items():
                if name in hints:
                    annotated_type = hints[name]

                    # PEP 428 discourages it by MyPy does not complain
                    if parameter.default is None:
                        annotated_type = Optional[annotated_type]

                    if parameter.kind == Parameter.VAR_POSITIONAL:
                        self.type_hints[name] = Tuple[annotated_type, ...]
                    elif parameter.kind == Parameter.VAR_KEYWORD:
                        self.type_hints[name] = Dict[str, annotated_type]
                    else:
                        self.type_hints[name] = annotated_type

            if 'return' in hints:
                self.type_hints['return'] = hints['return']

            _type_hints_map[func] = self.type_hints


def get_type_name(type_):
    # typing.* types don't have a __name__ on Python 3.7+
    return getattr(type_, '__name__', None) or type_._name


def find_function(frame) -> Optional[Callable]:
    """
    Return a function object from the garbage collector that matches the frame's code object.

    This process is unreliable as several function objects could use the same code object.
    Fortunately the likelihood of this happening with the combination of the function objects
    having different type annotations is a very rare occurrence.

    :param frame: a frame object
    :return: a function object if one was found, ``None`` if not

    """
    func = _functions_map.get(frame.f_code)
    if func is None:
        for obj in gc.get_referrers(frame.f_code):
            if inspect.isfunction(obj):
                if func is None:
                    # The first match was found
                    func = obj
                else:
                    # A second match was found
                    return None

        # Cache the result for future lookups
        if func is not None:
            _functions_map[frame.f_code] = func
        else:
            raise LookupError('target function not found')

    return func


def qualified_name(obj) -> str:
    """
    Return the qualified name (e.g. package.module.Type) for the given object.

    Builtins and types from the :mod:`typing` package get special treatment by having the module
    name stripped from the generated name.

    """
    type_ = obj if inspect.isclass(obj) else type(obj)
    module = type_.__module__
    qualname = type_.__qualname__
    return qualname if module in ('typing', 'builtins') else '{}.{}'.format(module, qualname)


def function_name(func: FunctionType) -> str:
    """
    Return the qualified name of the given function.

    Builtins and types from the :mod:`typing` package get special treatment by having the module
    name stripped from the generated name.

    """
    module = func.__module__
    qualname = func.__qualname__
    return qualname if module == 'builtins' else '{}.{}'.format(module, qualname)


def check_callable(argname: str, value, expected_type, memo: Optional[_CallMemo]) -> None:
    if not callable(value):
        raise TypeError('{} must be a callable'.format(argname))

    if expected_type.__args__:
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


def check_dict(argname: str, value, expected_type, memo: Optional[_CallMemo]) -> None:
    if not isinstance(value, dict):
        raise TypeError('type of {} must be a dict; got {} instead'.
                        format(argname, qualified_name(value)))

    key_type, value_type = getattr(expected_type, '__args__', expected_type.__parameters__)
    for k, v in value.items():
        check_type('keys of {}'.format(argname), k, key_type, memo)
        check_type('{}[{!r}]'.format(argname, k), v, value_type, memo)


def check_list(argname: str, value, expected_type, memo: Optional[_CallMemo]) -> None:
    if not isinstance(value, list):
        raise TypeError('type of {} must be a list; got {} instead'.
                        format(argname, qualified_name(value)))

    value_type = getattr(expected_type, '__args__', expected_type.__parameters__)[0]
    if value_type:
        for i, v in enumerate(value):
            check_type('{}[{}]'.format(argname, i), v, value_type, memo)


def check_sequence(argname: str, value, expected_type, memo: Optional[_CallMemo]) -> None:
    if not isinstance(value, collections.abc.Sequence):
        raise TypeError('type of {} must be a sequence; got {} instead'.
                        format(argname, qualified_name(value)))

    value_type = getattr(expected_type, '__args__', expected_type.__parameters__)[0]
    if value_type:
        for i, v in enumerate(value):
            check_type('{}[{}]'.format(argname, i), v, value_type, memo)


def check_set(argname: str, value, expected_type, memo: Optional[_CallMemo]) -> None:
    if not isinstance(value, collections.abc.Set):
        raise TypeError('type of {} must be a set; got {} instead'.
                        format(argname, qualified_name(value)))

    value_type = getattr(expected_type, '__args__', expected_type.__parameters__)[0]
    if value_type:
        for v in value:
            check_type('elements of {}'.format(argname), v, value_type, memo)


def check_tuple(argname: str, value, expected_type, memo: Optional[_CallMemo]) -> None:
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


def check_union(argname: str, value, expected_type, memo: Optional[_CallMemo]) -> None:
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

    typelist = ', '.join(get_type_name(t) for t in union_params)
    raise TypeError('type of {} must be one of ({}); got {} instead'.
                    format(argname, typelist, qualified_name(value)))


def check_class(argname: str, value, expected_type, memo: Optional[_CallMemo]) -> None:
    if not isclass(value):
        raise TypeError('type of {} must be a type; got {} instead'.format(
            argname, qualified_name(value)))

    # Needed on Python 3.7+
    if expected_type is Type:
        return

    expected_class = expected_type.__args__[0] if expected_type.__args__ else None
    if expected_class:
        if isinstance(expected_class, TypeVar):
            check_typevar(argname, value, expected_class, memo, True)
        elif not issubclass(value, expected_class):
            raise TypeError('{} must be a subclass of {}; got {} instead'.format(
                argname, qualified_name(expected_class), qualified_name(value)))


def check_typevar(argname: str, value, typevar: TypeVar, memo: Optional[_CallMemo],
                  subclass_check: bool = False) -> None:
    if memo is None:
        raise TypeError('encountered a TypeVar but a call memo was not provided')

    bound_type = memo.typevars.get(typevar, typevar.__bound__)
    value_type = value if subclass_check else type(value)
    subject = argname if subclass_check else 'type of ' + argname
    if bound_type is None:
        # The type variable hasn't been bound yet -- check that the given value matches the
        # constraints of the type variable, if any
        if typevar.__constraints__ and value_type not in typevar.__constraints__:
            typelist = ', '.join(get_type_name(t) for t in typevar.__constraints__
                                 if t is not object)
            raise TypeError('{} must be one of ({}); got {} instead'.
                            format(subject, typelist, qualified_name(value_type)))
    elif typevar.__covariant__ or typevar.__bound__:
        if not issubclass(value_type, bound_type):
            raise TypeError(
                '{} must be {} or one of its subclasses; got {} instead'.
                format(subject, qualified_name(bound_type), qualified_name(value_type)))
    elif typevar.__contravariant__:
        if not issubclass(bound_type, value_type):
            raise TypeError(
                '{} must be {} or one of its superclasses; got {} instead'.
                format(subject, qualified_name(bound_type), qualified_name(value_type)))
    else:  # invariant
        if value_type is not bound_type:
            raise TypeError(
                '{} must be exactly {}; got {} instead'.
                format(subject, qualified_name(bound_type), qualified_name(value_type)))

    if typevar not in memo.typevars:
        # Bind the type variable to a concrete type
        memo.typevars[typevar] = value_type


def check_number(argname: str, value, expected_type):
    if expected_type is complex and not isinstance(value, (complex, float, int)):
        raise TypeError('type of {} must be either complex, float or int; got {} instead'.
                        format(argname, qualified_name(value.__class__)))
    elif expected_type is float and not isinstance(value, (float, int)):
        raise TypeError('type of {} must be either float or int; got {} instead'.
                        format(argname, qualified_name(value.__class__)))


def check_io(argname: str, value, expected_type):
    if expected_type is TextIO:
        if not isinstance(value, TextIOBase):
            raise TypeError('type of {} must be a text based I/O object; got {} instead'.
                            format(argname, qualified_name(value.__class__)))
    elif expected_type is BinaryIO:
        if not isinstance(value, (RawIOBase, BufferedIOBase)):
            raise TypeError('type of {} must be a binary I/O object; got {} instead'.
                            format(argname, qualified_name(value.__class__)))
    elif not isinstance(value, IOBase):
        raise TypeError('type of {} must be an I/O object; got {} instead'.
                        format(argname, qualified_name(value.__class__)))


# Equality checks are applied to these
origin_type_checkers = {
    Callable: check_callable,
    collections.abc.Callable: check_callable,
    dict: check_dict,
    Dict: check_dict,
    list: check_list,
    List: check_list,
    Sequence: check_sequence,
    collections.abc.Sequence: check_sequence,
    set: check_set,
    Set: check_set,
    tuple: check_tuple,
    Tuple: check_tuple,
    type: check_class,
    Union: check_union
}
_subclass_check_unions = hasattr(Union, '__union_set_params__')
if Type is not None:
    origin_type_checkers[Type] = check_class


def check_type(argname: str, value, expected_type, memo: Optional[_CallMemo] = None) -> None:
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

    origin_type = getattr(expected_type, '__origin__', None)
    if origin_type is not None:
        checker_func = origin_type_checkers.get(origin_type)
        if checker_func:
            checker_func(argname, value, expected_type, memo)
        else:
            check_type(argname, value, origin_type, memo)
    elif isclass(expected_type):
        if issubclass(expected_type, Tuple):
            check_tuple(argname, value, expected_type, memo)
        elif issubclass(expected_type, Callable) and hasattr(expected_type, '__args__'):
            # Needed on Python 3.5.0 to 3.5.2
            check_callable(argname, value, expected_type, memo)
        elif issubclass(expected_type, (float, complex)):
            check_number(argname, value, expected_type)
        elif _subclass_check_unions and issubclass(expected_type, Union):
            check_union(argname, value, expected_type, memo)
        elif isinstance(expected_type, TypeVar):
            check_typevar(argname, value, expected_type, memo)
        elif issubclass(expected_type, IO):
            check_io(argname, value, expected_type)
        else:
            expected_type = (getattr(expected_type, '__extra__', None) or origin_type or
                             expected_type)
            if not isinstance(value, expected_type):
                raise TypeError(
                    'type of {} must be {}; got {} instead'.
                    format(argname, qualified_name(expected_type), qualified_name(value)))
    elif isinstance(expected_type, TypeVar):
        # Only happens on < 3.6
        check_typevar(argname, value, expected_type, memo)
    elif (isfunction(expected_type) and
            getattr(expected_type, "__module__", None) == "typing" and
            getattr(expected_type, "__qualname__", None).startswith("NewType.") and
            hasattr(expected_type, "__supertype__")):
        # typing.NewType, should check against supertype (recursively)
        return check_type(argname, value, expected_type.__supertype__, memo)


def check_return_type(retval, memo: Optional[_CallMemo]) -> bool:
    if 'return' in memo.type_hints:
        try:
            check_type('the return value', retval, memo.type_hints['return'], memo)
        except TypeError as exc:  # suppress unnecessarily long tracebacks
            raise TypeError(exc) from None

    return True


def check_argument_types(memo: Optional[_CallMemo] = None) -> bool:
    """
    Check that the argument values match the annotated types.

    Unless both ``args`` and ``kwargs`` are provided, the information will be retrieved from
    the previous stack frame (ie. from the function that called this).

    :return: ``True``
    :raises TypeError: if there is an argument type mismatch

    """
    if memo is None:
        frame = inspect.currentframe().f_back
        try:
            func = find_function(frame)
        except LookupError:
            return True  # This can happen with the Pydev/PyCharm debugger extension installed

        memo = _CallMemo(func, frame)

    for argname, expected_type in memo.type_hints.items():
        if argname != 'return' and argname in memo.arguments:
            value = memo.arguments[argname]
            description = 'argument "{}"'.format(argname)
            try:
                check_type(description, value, expected_type, memo)
            except TypeError as exc:  # suppress unnecessarily long tracebacks
                raise TypeError(exc) from None

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
        warn('no type annotations present -- not typechecking {}'.format(function_name(func)))
        return func

    def wrapper(*args, **kwargs):
        memo = _CallMemo(func, args=args, kwargs=kwargs)
        check_argument_types(memo)
        retval = func(*args, **kwargs)
        check_return_type(retval, memo)
        return retval

    async def async_wrapper(*args, **kwargs):
        memo = _CallMemo(func, args=args, kwargs=kwargs)
        check_argument_types(memo)
        retval = await func(*args, **kwargs)
        check_return_type(retval, memo)
        return retval

    if inspect.iscoroutinefunction(func):
        return wraps(func)(async_wrapper)
    else:
        return wraps(func)(wrapper)


class TypeWarning(UserWarning):
    """
    A warning that is emitted when a type check fails.

    :ivar str event: ``call`` or ``return``
    :ivar Callable func: the function in which the violation occurred (the called function if event
        is ``call``, or the function where a value of the wrong type was returned from if event is
        ``return``)
    :ivar str error: the error message contained by the caught :cls:`TypeError`
    :ivar frame: the frame in which the violation occurred
    """

    __slots__ = ('func', 'event', 'message', 'frame')

    def __init__(self, memo: Optional[_CallMemo], event: str, frame,
                 exception: TypeError):  # pragma: no cover
        self.func = memo.func
        self.event = event
        self.error = str(exception)
        self.frame = frame

        if self.event == 'call':
            caller_frame = self.frame.f_back
            event = 'call to {}() from {}:{}'.format(
                function_name(self.func), caller_frame.f_code.co_filename, caller_frame.f_lineno)
        else:
            event = 'return from {}() at {}:{}'.format(
                function_name(self.func), self.frame.f_code.co_filename, self.frame.f_lineno)

        super().__init__('[{thread_name}] {event}: {self.error}'.format(
            thread_name=threading.current_thread().name, event=event, self=self))

    @property
    def stack(self):
        """Return the stack where the last frame is from the target function."""
        return extract_stack(self.frame)

    def print_stack(self, file: TextIO = None, limit: int = None) -> None:
        """
        Print the traceback from the stack frame where the target function was run.

        :param file: an open file to print to (prints to stdout if omitted)
        :param limit: the maximum number of stack frames to print

        """
        print_stack(self.frame, limit, file)


class TypeChecker:
    """
    A type checker that collects type violations by hooking into ``sys.setprofile()``.

    :param all_threads: ``True`` to check types in all threads created while the checker is
        running, ``False`` to only check in the current one
    """

    def __init__(self, packages: Union[str, Sequence[str]], *, all_threads: bool = True):
        assert check_argument_types()
        self.all_threads = all_threads
        self._call_memos = {}  # type: Dict[Any, _CallMemo]
        self._previous_profiler = None
        self._previous_thread_profiler = None
        self._active = False

        if isinstance(packages, str):
            self._packages = (packages,)
        else:
            self._packages = tuple(packages)

    @property
    def active(self) -> bool:
        """Return ``True`` if currently collecting type violations."""
        return self._active

    def should_check_type(self, func: Callable) -> bool:
        if not func.__annotations__:
            # No point in checking if there are no type hints
            return False
        else:
            # Check types if the module matches any of the package prefixes
            return any(func.__module__ == package or func.__module__.startswith(package + '.')
                       for package in self._packages)

    def start(self):
        if self._active:
            raise RuntimeError('type checker already running')

        self._active = True

        # Install this instance as the current profiler
        self._previous_profiler = sys.getprofile()
        sys.setprofile(self)

        # If requested, set this instance as the default profiler for all future threads
        # (does not affect existing threads)
        if self.all_threads:
            self._previous_thread_profiler = threading._profile_hook
            threading.setprofile(self)

    def stop(self):
        if self._active:
            if sys.getprofile() is self:
                sys.setprofile(self._previous_profiler)
            else:  # pragma: no cover
                warn('the system profiling hook has changed unexpectedly')

            if self.all_threads:
                if threading._profile_hook is self:
                    threading.setprofile(self._previous_thread_profiler)
                else:  # pragma: no cover
                    warn('the threading profiling hook has changed unexpectedly')

            self._active = False

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def __call__(self, frame, event: str, arg) -> None:  # pragma: no cover
        if not self._active:
            # This happens if all_threads was enabled and a thread was created when the checker was
            # running but was then stopped. The thread's profiler callback can't be reset any other
            # way but this.
            sys.setprofile(self._previous_thread_profiler)
            return

        # If an actual profiler is running, don't include the type checking times in its results
        if event == 'call':
            try:
                func = find_function(frame)
            except Exception:
                func = None

            if func is not None and self.should_check_type(func):
                memo = self._call_memos[frame] = _CallMemo(func, frame)
                try:
                    check_argument_types(memo)
                except TypeError as exc:
                    warn(TypeWarning(memo, event, frame, exc))

            if self._previous_profiler is not None:
                self._previous_profiler(frame, event, arg)
        elif event == 'return':
            if self._previous_profiler is not None:
                self._previous_profiler(frame, event, arg)

            memo = self._call_memos.pop(frame, None)
            if memo is not None:
                try:
                    check_return_type(arg, memo)
                except TypeError as exc:
                    warn(TypeWarning(memo, event, frame, exc))
        elif self._previous_profiler is not None:
            self._previous_profiler(frame, event, arg)
