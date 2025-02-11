"""
Checkers for types
"""

from __future__ import annotations

import collections.abc
import dataclasses
import typing

import result

from . import predicates


@dataclasses.dataclass(slots=True, frozen=True)
@typing.final
class Type[PyTypeT]:
    """
    Type of ulna configuration format types.
    """

    name: str
    check: TypecheckingFunction[typing.Any | None, PyTypeT]

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
        refined_check: TypecheckingFunction[PyTypeT, RefinedPyTypeT],
    ) -> Type[RefinedPyTypeT]:
        """
        Return a new type that refines the current one by adding
        an additional check.

        If the base type check fails, the refined check will not
        be performed at all.
        """

        def check(
            data: typing.Any | None,
        ) -> result.Result[RefinedPyTypeT, TypecheckingError]:
            base_check_result = self.check(data)

            if isinstance(base_check_result, result.Err):
                return base_check_result

            return refined_check(base_check_result.unwrap())

        return Type(name, check)

    @staticmethod
    def from_predicate[T](
        name: str,
        predicate: typing.Callable[
            [typing.Any | None], typing.TypeGuard[T]
        ],
    ) -> Type[T]:
        """
        Construct a type with `name` given a `predicate`.
        """

        def checking_function(
            data: typing.Any | None,
        ) -> result.Result[T, TypecheckingError]:
            if not predicate(data):
                found_type = from_pytype(data.__class__)

                return result.Err(
                    MismatchedTypesError(
                        name,
                        found_type.name,
                    ),
                )

            return result.Ok(data)

        return Type(name, checking_function)


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


@dataclasses.dataclass(slots=True, frozen=True)
class MismatchedTypesError:
    """
    A certain type was expected, but we found another one.
    """

    expected: str
    found: str


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
    expected_type: str


@dataclasses.dataclass(slots=True, frozen=True)
@typing.final
class UnexpectedFieldError:
    """
    The section did not expect that field.
    """

    field_name: str


type TypecheckingError = (
    MismatchedTypesError
    | WrongItemTypeError
    | WrongFieldTypeError
    | MissingFieldError
    | UnexpectedFieldError
)

type TypecheckingFunction[InputT, OutputT] = typing.Callable[
    [InputT],
    result.Result[OutputT, TypecheckingError],
]


def checker_from_predicate[PyTypeT](
    name: str,
    predicate: typing.Callable[
        [typing.Any | None],
        typing.TypeGuard[PyTypeT],
    ],
) -> TypecheckingFunction[typing.Any | None, PyTypeT]:
    """
    Make a checking function from a `name` and a `predicate`.
    """

    def checking_function(
        data: typing.Any | None,
    ) -> result.Result[PyTypeT, TypecheckingError]:
        if not predicate(data):
            found_type = from_pytype(data.__class__)

            return result.Err(MismatchedTypesError(name, found_type.name))

        return result.Ok(data)

    return checking_function


# this function is private because it is inherently unsafe since
# we do not have higher-kinded type variables, that is, we
# cannot express (Foo[Any]) -> Foo[T] where Foo is a "generic"
# type variable - therefore we have to abuse the dynamic Any
def _check_all_sequence_items[
    PySequenceTypeT: collections.abc.Sequence[typing.Any],
    PyTypeT,
](
    data: PySequenceTypeT,
    *,
    item_type: Type[PyTypeT],
) -> result.Result[
    PySequenceTypeT,
    TypecheckingError,
]:
    """
    Type-check all the items of a sequence `data` given their
    expected type `item_type`.
    """

    for index, item in enumerate(data):
        if not item_type.is_inhabited_by(item):
            found_item_type = from_pytype(item.__class__)

            return result.Err(
                WrongItemTypeError(
                    item_type.name,
                    found_item_type.name,
                    index,
                )
            )

    return result.Ok(data)


def make_list_checker[PyTypeT](
    name: str,
    *,
    item_type: Type[PyTypeT],
) -> TypecheckingFunction[typing.Any | None, list[PyTypeT]]:
    """
    Create a specialized list checker given its item type `item_type`.
    """

    specialized_name = f"{name}({item_type.name})"

    def checker(
        data: typing.Any | None,
    ) -> result.Result[list[PyTypeT], TypecheckingError]:
        if not predicates.is_list(data):
            found_type = from_pytype(data.__class__)

            return result.Err(
                MismatchedTypesError(
                    specialized_name,
                    found_type.name,
                )
            )

        return _check_all_sequence_items(data, item_type=item_type)

    return checker


def from_pytype[PyTypeT](pytype: type[PyTypeT]) -> Type[PyTypeT]:
    pass
