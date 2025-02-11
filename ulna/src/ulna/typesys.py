"""
ulna configuration format type system (v2)
"""

from __future__ import annotations

import dataclasses
import typing

import result

from . import predicates


@dataclasses.dataclass(slots=True, frozen=True)
class MismatchedTypesError:
    """
    A certain type was expected, but we found another one.
    """

    expected: AnyType
    found: AnyType


@dataclasses.dataclass(slots=True, frozen=True)
@typing.final
class WrongItemTypeError(MismatchedTypesError):
    """
    The list item does not have the expected type.
    """

    index: int


@dataclasses.dataclass(slots=True, frozen=True)
@typing.final
class WrongFieldTypeError(MismatchedTypesError):
    """
    The section field was expecting a different type.
    """

    field_name: str


@dataclasses.dataclass(slots=True, frozen=True)
@typing.final
class MissingFieldError:
    """
    The section expected a field that was not present.
    """

    field_name: str
    expected_type: AnyType


@dataclasses.dataclass(slots=True, frozen=True)
@typing.final
class UnexpectedFieldError:
    """
    The section did not expect that field.
    """

    field_name: str


type TypecheckError = (
    MismatchedTypesError
    | WrongItemTypeError
    | WrongFieldTypeError
    | MissingFieldError
    | UnexpectedFieldError
)


@dataclasses.dataclass(slots=True, frozen=True)
@typing.final
class Type[PyTypeT]:
    """
    Type of ulna configuration format types.
    """

    name: str
    check: CheckingFunction[typing.Any | None, PyTypeT]

    def is_inhabited_by(
        self,
        value: typing.Any | None,
    ) -> typing.TypeGuard[PyTypeT]:
        """
        Return whether `value` is of the type.
        """

        return self.check(value).is_ok()

    def refine[RefinedPyTypeT](
        self,
        name: str,
        refined_check: CheckingFunction[PyTypeT, RefinedPyTypeT],
    ) -> Type[RefinedPyTypeT]:
        """
        Return a new type that refines the current one by adding
        an additional check.

        If the base type check fails, the refined check will not
        be performed at all.
        """

        def check(
            data: typing.Any | None,
        ) -> result.Result[RefinedPyTypeT, TypecheckError]:
            base_check_result = self.check(data)

            if isinstance(base_check_result, result.Err):
                return base_check_result

            return refined_check(base_check_result.unwrap())

        return Type(name, check)


@dataclasses.dataclass(slots=True, frozen=True)
@typing.final
class TypeFunctor[IT, OT]:
    """
    Type of parametric types.
    """

    name: str
    function: typing.Callable[[str, Type[IT]], Type[OT]]

    def __call__(self, item_type: Type[IT], /) -> Type[OT]:
        """
        Create a specialized instance of the parametric type
        given the type `item_type`.
        """

        return self.function(self.name, item_type)


def checking_for[PyTypeT](
    name: str,
) -> typing.Callable[
    [
        typing.Callable[
            [Type[PyTypeT], typing.Any | None],
            result.Result[PyTypeT, TypecheckError],
        ]
    ],
    Type[PyTypeT],
]:
    """
    Mark a function as checking for a certain type by allowing
    said type to be passed as the first argument of the checking
    function.
    """

    def decorator(
        method: typing.Callable[
            [Type[PyTypeT], typing.Any | None],
            result.Result[PyTypeT, TypecheckError],
        ],
    ) -> Type[PyTypeT]:
        def checker(
            data: typing.Any | None,
        ) -> result.Result[PyTypeT, TypecheckError]:
            return method(Type(name, checker), data)

        return Type(name, checker)

    return decorator


def _make_list_type[PyTypeT](
    name: str,
    item_type: Type[PyTypeT],
) -> Type[list[PyTypeT]]:
    """
    Create a list type where items are of the type `ty`.
    """

    @checking_for(name)
    def _check_any_list(
        self: Type[list[typing.Any]],
        data: typing.Any | None,
    ) -> result.Result[list[typing.Any], TypecheckError]:
        if not predicates.is_list(data):
            found_type = from_pytype(data.__class__)

            return result.Err(MismatchedTypesError(self, found_type))

        return result.Ok(data)

    def items_check(
        data: list[typing.Any],
    ) -> result.Result[list[PyTypeT], TypecheckError]:
        for index, item in enumerate(data):
            if not item_type.is_inhabited_by(item):
                found_item_type = from_pytype(item.__class__)

                return result.Err(
                    WrongItemTypeError(
                        item_type,
                        found_item_type,
                        index,
                    ),
                )

        return result.Ok(data)

    return _check_any_list.refine(f"{name}({item_type.name})", items_check)


List: typing.Final = TypeFunctor("List", _make_list_type)


type AnyType = Type[typing.Any]
type CheckingFunction[InputT, OutputT] = typing.Callable[
    [InputT], result.Result[OutputT, TypecheckError]
]


def from_pytype[PyTypeT](pytype: type[PyTypeT]) -> Type[PyTypeT]:
    pass
