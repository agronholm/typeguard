import collections.abc
import inspect
import sys
import warnings
from enum import Enum
from inspect import Parameter, isclass, isfunction
from io import BufferedIOBase, IOBase, RawIOBase, TextIOBase
from textwrap import indent
from typing import (
    IO, AbstractSet, Any, BinaryIO, Callable, Dict, ForwardRef, List, NewType, Optional, Sequence,
    Set, TextIO, Tuple, Type, TypeVar, Union)

from .exceptions import TypeCheckError, TypeHintWarning
from .memo import TypeCheckMemo
from .utils import (
    evaluate_forwardref, get_args, get_origin, get_type_name, is_typeddict, qualified_name)

if sys.version_info >= (3, 9):
    from typing import Annotated, get_type_hints
else:
    from typing_extensions import Annotated, get_type_hints

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal


TypeCheckerCallable = Callable[[Any, Any, TypeCheckMemo], Any]
TypeCheckLookupCallback = Callable[[Any, tuple, tuple], Optional[TypeCheckerCallable]]

# Sentinel
_missing = object()

# Lifted from mypy.sharedparse
BINARY_MAGIC_METHODS = {
    "__add__",
    "__and__",
    "__cmp__",
    "__divmod__",
    "__div__",
    "__eq__",
    "__floordiv__",
    "__ge__",
    "__gt__",
    "__iadd__",
    "__iand__",
    "__idiv__",
    "__ifloordiv__",
    "__ilshift__",
    "__imatmul__",
    "__imod__",
    "__imul__",
    "__ior__",
    "__ipow__",
    "__irshift__",
    "__isub__",
    "__itruediv__",
    "__ixor__",
    "__le__",
    "__lshift__",
    "__lt__",
    "__matmul__",
    "__mod__",
    "__mul__",
    "__ne__",
    "__or__",
    "__pow__",
    "__radd__",
    "__rand__",
    "__rdiv__",
    "__rfloordiv__",
    "__rlshift__",
    "__rmatmul__",
    "__rmod__",
    "__rmul__",
    "__ror__",
    "__rpow__",
    "__rrshift__",
    "__rshift__",
    "__rsub__",
    "__rtruediv__",
    "__rxor__",
    "__sub__",
    "__truediv__",
    "__xor__",
}


def check_callable(value: Any, origin_type: Any, args: Tuple[Any, ...],
                   memo: TypeCheckMemo) -> None:
    if not callable(value):
        raise TypeCheckError('is not callable')

    if args:
        try:
            signature = inspect.signature(value)
        except (TypeError, ValueError):
            return

        argument_types = args[0]
        if argument_types != (Ellipsis,):
            # The callable must not have keyword-only arguments without defaults
            unfulfilled_kwonlyargs = [
                param.name for param in signature.parameters.values() if
                param.kind == Parameter.KEYWORD_ONLY and param.default == Parameter.empty]
            if unfulfilled_kwonlyargs:
                raise TypeCheckError(
                    f'has mandatory keyword-only arguments in its declaration: '
                    f'{", ".join(unfulfilled_kwonlyargs)}')

            num_mandatory_args = len([
                param.name for param in signature.parameters.values()
                if param.kind in (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD) and
                param.default is Parameter.empty])
            has_varargs = any(param for param in signature.parameters.values()
                              if param.kind == Parameter.VAR_POSITIONAL)

            if num_mandatory_args > len(argument_types):
                raise TypeCheckError(
                    f'has too many arguments in its declaration; expected {len(argument_types)} '
                    f'but {num_mandatory_args} argument(s) declared')
            elif not has_varargs and num_mandatory_args < len(argument_types):
                raise TypeCheckError(
                    f'has too few arguments in its declaration; expected {len(argument_types)} '
                    f'but {num_mandatory_args} argument(s) declared')


def check_dict(value: Any, origin_type: Any, args: Tuple[Any, ...], memo: TypeCheckMemo) -> None:
    if not isinstance(value, dict):
        raise TypeCheckError('value is not a dict')

    if args:
        key_type, value_type = args
        if key_type is not Any or value_type is not Any:
            for k, v in value.items():
                check_type_internal(k, key_type, memo)
                check_type_internal(v, value_type, memo)


def check_typed_dict(value: Any, origin_type: Any, args: Tuple[Any, ...],
                     memo: TypeCheckMemo) -> None:
    declared_keys = frozenset(origin_type.__annotations__)
    if hasattr(origin_type, '__required_keys__'):
        required_keys = origin_type.__required_keys__
    else:  # py3.8 and lower
        required_keys = declared_keys if origin_type.__total__ else frozenset()

    existing_keys = frozenset(value)
    extra_keys = existing_keys - declared_keys
    if extra_keys:
        keys_formatted = ', '.join('"{}"'.format(key) for key in sorted(extra_keys))
        raise TypeCheckError(f'has unexpected extra key(s): {keys_formatted}')

    missing_keys = required_keys - existing_keys
    if missing_keys:
        keys_formatted = ', '.join('"{}"'.format(key) for key in sorted(missing_keys))
        raise TypeCheckError(f'is missing required key(s): {keys_formatted}')

    for key, argtype in get_type_hints(origin_type).items():
        argvalue = value.get(key, _missing)
        if argvalue is not _missing:
            check_type_internal(argvalue, argtype, memo)


def check_list(value: Any, origin_type: Any, args: Tuple[Any, ...], memo: TypeCheckMemo) -> None:
    if not isinstance(value, list):
        raise TypeCheckError('is not a list')

    if args and args != (Any,):
        for i, v in enumerate(value):
            check_type_internal(v, args[0], memo)


def check_sequence(value: Any, origin_type: Any, args: Tuple[Any, ...],
                   memo: TypeCheckMemo) -> None:
    if not isinstance(value, collections.abc.Sequence):
        raise TypeCheckError('is not a sequence')

    if args and args != (Any,):
        for i, v in enumerate(value):
            check_type_internal(v, args[0], memo)


def check_set(value: Any, origin_type: Any, args: Tuple[Any, ...], memo: TypeCheckMemo) -> None:
    if not isinstance(value, AbstractSet):
        raise TypeCheckError('is not a set')

    if args and args != (Any,):
        for v in value:
            check_type_internal(v, args[0], memo)


def check_tuple(value: Any, origin_type: Any, args: Tuple[Any, ...], memo: TypeCheckMemo) -> None:
    # Specialized check for NamedTuples
    field_types = getattr(origin_type, '__annotations__', None)
    if field_types is None and sys.version_info < (3, 8):
        field_types = getattr(origin_type, '_field_types', None)

    if field_types:
        if not isinstance(value, origin_type):
            raise TypeCheckError(f'is not a named tuple of type {qualified_name(origin_type)}')

        for name, field_type in field_types.items():
            check_type_internal(getattr(value, name), field_type, memo)

        return
    elif not isinstance(value, tuple):
        raise TypeCheckError('is not a tuple')

    if args:
        # Python 3.6+
        use_ellipsis = args[-1] is Ellipsis
        tuple_params = args[:-1 if use_ellipsis else None]
    else:
        # Unparametrized Tuple or plain tuple
        return

    if use_ellipsis:
        element_type = tuple_params[0]
        for i, element in enumerate(value):
            check_type_internal(element, element_type, memo)
    elif tuple_params == ((),):
        if value != ():
            raise TypeCheckError('is not an empty tuple')
    else:
        if len(value) != len(tuple_params):
            raise TypeCheckError(
                f'has wrong number of elements (expected {len(tuple_params)}, got {len(value)} '
                f'instead)')

        for i, (element, element_type) in enumerate(zip(value, tuple_params)):
            check_type_internal(element, element_type, memo)


def check_union(value: Any, origin_type: Any, args: Tuple[Any, ...], memo: TypeCheckMemo) -> None:
    errors: Dict[str, TypeCheckError] = {}
    for type_ in args:
        try:
            check_type_internal(value, type_, memo)
            return
        except TypeCheckError as exc:
            errors[get_type_name(type_)] = exc

    formatted_errors = indent('\n'.join(f'{key}: {error}' for key, error in errors.items()), '  ')
    raise TypeCheckError(f'did not match any element in the union:\n{formatted_errors}')


def check_class(value: Any, origin_type: Any, args: Tuple[Any, ...], memo: TypeCheckMemo) -> None:
    if not isclass(value):
        raise TypeCheckError('is not a class')

    # Needed on Python 3.7+
    if not args:
        return

    expected_class = args[0]
    if isinstance(expected_class, TypeVar):
        check_typevar(value, expected_class, (), memo, subclass_check=True)
    elif get_origin(expected_class) is Union:
        errors: Dict[str, TypeCheckError] = {}
        for arg in get_args(expected_class):
            if arg is Any:
                return

            try:
                check_class(value, type, (arg,), memo)
                return
            except TypeCheckError as exc:
                errors[get_type_name(arg)] = exc
        else:
            formatted_errors = indent(
                '\n'.join(f'{key}: {error}' for key, error in errors.items()), '  ')
            raise TypeCheckError(f'did not match any element in the union:\n{formatted_errors}')
    elif not issubclass(value, expected_class):
        raise TypeCheckError(f'is not a subclass of {qualified_name(expected_class)}')


def check_newtype(value: Any, origin_type: Any, args: Tuple[Any, ...],
                  memo: TypeCheckMemo) -> None:
    supertype = origin_type.__supertype__
    if not isinstance(value, supertype):
        raise TypeCheckError(f'is not an instance of {qualified_name(supertype)}')


def check_instance(value: Any, origin_type: Any, args: Tuple[Any, ...],
                   memo: TypeCheckMemo) -> None:
    if not isinstance(value, origin_type):
        raise TypeCheckError(f'is not an instance of {qualified_name(origin_type)}')


def check_typevar(value: Any, origin_type: TypeVar, args: Tuple[Any, ...], memo: TypeCheckMemo, *,
                  subclass_check: bool = False) -> None:
    if origin_type.__bound__ is not None:
        annotation = Type[origin_type.__bound__] if subclass_check else origin_type.__bound__
        check_type_internal(value, annotation, memo)
    elif origin_type.__constraints__:
        for constraint in origin_type.__constraints__:
            annotation = Type[constraint] if subclass_check else constraint
            try:
                check_type_internal(value, annotation, memo)
            except TypeCheckError:
                pass
            else:
                break
        else:
            formatted_constraints = ', '.join(get_type_name(constraint)
                                              for constraint in origin_type.__constraints__)
            raise TypeCheckError(f'does not match any of the constraints '
                                 f'({formatted_constraints})')


def check_literal(value: Any, origin_type: Any, args: Tuple[Any, ...],
                  memo: TypeCheckMemo) -> None:
    def get_literal_args(literal_args: Tuple[Any, ...]) -> Tuple[Any, ...]:
        retval = []
        for arg in literal_args:
            if get_origin(arg) is Literal:
                # The first check works on py3.6 and lower, the second one on py3.7+
                retval.extend(get_literal_args(arg.__args__))
            elif arg is None or isinstance(arg, (int, str, bytes, bool, Enum)):
                retval.append(arg)
            else:
                raise TypeError(f'Illegal literal value: {arg}')  # TypeError here is deliberate

        return tuple(retval)

    final_args = tuple(get_literal_args(args))
    if value not in final_args:
        formatted_args = ', '.join(repr(arg) for arg in final_args)
        raise TypeCheckError(f'is not any of ({formatted_args})')


def check_number(value: Any, origin_type: Any, args: Tuple[Any, ...], memo: TypeCheckMemo) -> None:
    if origin_type is complex and not isinstance(value, (complex, float, int)):
        raise TypeCheckError('is neither complex, float or int')
    elif origin_type is float and not isinstance(value, (float, int)):
        raise TypeCheckError('is neither float or int')


def check_io(value: Any, origin_type: Any, args: Tuple[Any, ...], memo: TypeCheckMemo) -> None:
    if origin_type is TextIO or (origin_type is IO and args == (str,)):
        if not isinstance(value, TextIOBase):
            raise TypeCheckError('is not a text based I/O object')
    elif origin_type is BinaryIO or (origin_type is IO and args == (bytes,)):
        if not isinstance(value, (RawIOBase, BufferedIOBase)):
            raise TypeCheckError('is not a binary I/O object')
    elif not isinstance(value, IOBase):
        raise TypeCheckError('is not an I/O object')


def check_protocol(value: Any, origin_type: Any, args: Tuple[Any, ...],
                   memo: TypeCheckMemo) -> None:
    # TODO: implement proper compatibility checking and support non-runtime protocols
    if getattr(origin_type, '_is_runtime_protocol', False):
        if not isinstance(value, origin_type):
            raise TypeCheckError(f'is not compatible with the {origin_type.__qualname__} protocol')


def check_byteslike(value: Any, origin_type: Any, args: Tuple[Any, ...],
                    memo: TypeCheckMemo) -> None:
    if not isinstance(value, (bytearray, bytes, memoryview)):
        raise TypeCheckError('is not bytes-like')


def check_instanceof(value: Any, origin_type: Any, args: Tuple[Any, ...],
                     memo: TypeCheckMemo) -> None:
    if not isinstance(value, origin_type):
        raise TypeCheckError(f'is not an instance of {qualified_name(origin_type)}')


def check_type_internal(value: Any, annotation: Any, memo: TypeCheckMemo) -> None:
    from . import config

    if isinstance(annotation, ForwardRef):
        try:
            annotation = evaluate_forwardref(annotation, memo)
        except NameError:
            if config._config.forward_ref_policy is config.ForwardRefPolicy.ERROR:
                raise
            elif config._config.forward_ref_policy is config.ForwardRefPolicy.WARN:
                warnings.warn(f'Cannot resolve forward reference {annotation}', TypeHintWarning)

            return

    origin_type = get_origin(annotation)
    if origin_type is Annotated:
        annotation, *extras = get_args(annotation)
        origin_type = get_origin(annotation)
    else:
        extras = ()

    if origin_type is not None:
        args = get_args(annotation)
    else:
        origin_type = annotation
        args = ()

    for lookup_func in config._config.checker_lookup_functions:
        checker = lookup_func(origin_type, args, extras)
        if checker:
            checker(value, origin_type, args, memo)
            return

    if not isinstance(value, origin_type):
        raise TypeCheckError(f'is not an instance of {qualified_name(origin_type)}')


# Equality checks are applied to these
origin_type_checkers = {
    bytes: check_byteslike,
    AbstractSet: check_set,
    BinaryIO: check_io,
    Callable: check_callable,
    collections.abc.Callable: check_callable,
    complex: check_number,
    dict: check_dict,
    Dict: check_dict,
    float: check_number,
    IO: check_io,
    list: check_list,
    List: check_list,
    Literal: check_literal,
    Sequence: check_sequence,
    collections.abc.Sequence: check_sequence,
    collections.abc.Set: check_set,
    set: check_set,
    Set: check_set,
    TextIO: check_io,
    tuple: check_tuple,
    Tuple: check_tuple,
    type: check_class,
    Type: check_class,
    Union: check_union
}


def builtin_checker_lookup(
    origin_type: Any, args: tuple, extras: tuple
) -> Optional[TypeCheckerCallable]:
    checker = origin_type_checkers.get(origin_type)
    if checker is not None:
        return checker
    elif is_typeddict(origin_type):
        return check_typed_dict
    elif isclass(origin_type) and issubclass(origin_type, Tuple):  # NamedTuple
        return check_tuple
    elif getattr(origin_type, '_is_protocol', False):
        return check_protocol
    elif isinstance(origin_type, TypeVar):
        return check_typevar
    elif origin_type.__class__ is NewType:
        # typing.NewType on Python 3.10+
        return check_newtype
    elif (isfunction(origin_type) and
            getattr(origin_type, "__module__", None) == "typing" and
            getattr(origin_type, "__qualname__", None).startswith("NewType.") and
            hasattr(origin_type, "__supertype__")):
        # typing.NewType on Python 3.9 and below
        return check_newtype

    return None
