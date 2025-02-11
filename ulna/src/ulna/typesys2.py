"""
Type system of ulna's configuration format.
"""

from __future__ import annotations

import dataclasses
import enum
import types
import typing

import option

from . import predicates

ItemT_co = typing.TypeVar("ItemT_co", bound="Type", covariant=True)


class ScalarType(enum.Enum):
    """
    A scalar type is a type made of one component.
    """

    Never = enum.auto()
    String = enum.auto()
    ProjectIdentifier = enum.auto()
    CompilerName = enum.auto()


@dataclasses.dataclass(slots=True, frozen=True)
@typing.final
class List[ItemT: Type]:
    """
    Ordered sequence of items.
    """

    item_type: ItemT


# very unfortunately, we have to use the OG Generic instead of
# the nice PEP 695 notation because it does not infer covariance
@dataclasses.dataclass(slots=True, frozen=True)
@typing.final
class Optional(typing.Generic[ItemT_co]):
    """
    Represents the item that may not be present.
    """

    item_type: ItemT_co


@dataclasses.dataclass(slots=True, frozen=True)
@typing.final
class Section:
    """
    Sequence of names associated with values, which pairs are
    called fields.
    """

    fields: dict[str, Type]


type Type = ScalarType | List[Type] | Optional[Type] | Section


def from_python_type[T](  # noqa: C901, PLR0911, PLR0912
    python_type: type[T],
    *,
    data: T | None = None,
) -> option.Option[Type]:
    """
    Return the ulna type associated with the given python type
    if there is one.

    `data` can be provided for getting a more refined result.
    """

    if python_type is str:
        if predicates.is_compiler_name(data):
            return option.Some(ScalarType.CompilerName)

        if predicates.is_project_identifier(data):
            return option.Some(ScalarType.ProjectIdentifier)

        # either the value was not provided, or it is just a
        # simple string, so we can't refine much
        return option.Some(ScalarType.String)

    # this is where things get tricky: we want to introspect
    # type parameters at runtime to get the most precise type
    # possible
    if isinstance(python_type, types.GenericAlias):
        # *- List -* #

        if python_type.__origin__ is list:
            # if we have `value`, we could potentially try to
            # get the most refined type of each item, take the
            # broadest and declare it as the item type, but this
            # is far from simple - the dumb type is probably
            # good enough, and we don't actually use anything
            # else than lists of strings anyway lol
            (item_python_type,) = python_type.__args__
            item_type_maybe = from_python_type(item_python_type)

            # ulna has lists but this one might have items of a
            # type that does not have a ulna equivalent
            if isinstance(item_type_maybe, option.Nothing):
                return option.Nothing()

            return option.Some(List(item_type_maybe.unwrap()))

        # *- Optional -* #

        if python_type.__origin__ is option.Some:
            # this time we will actually try to refine it with
            # `value` if provided!
            (item_python_type,) = python_type.__args__

            if data is not None:
                # praying that the user didn't lie by passing
                # `Some` for `python_type` but a `Nothing` for
                # the value...
                item = typing.cast(
                    "option.Some[typing.Any]",
                    data,
                ).unwrap()
            else:
                item = None

            item_type_maybe = from_python_type(
                item_python_type,
                data=item,
            )

            if isinstance(item_type_maybe, option.Nothing):
                return option.Nothing()

            return option.Some(Optional(item_type_maybe.unwrap()))

        if python_type.__origin__ is option.Nothing:
            # there is no way to figure out the Option type
            # parameter at runtime :(
            # but since the wrapped value is never reached we
            # can just give it the bottom type I guess
            return option.Some(Optional(ScalarType.Never))

        # *- Section -* #

        if python_type.__origin__ is dict:
            # there is no such thing as a non-specialized dict
            if data is None:
                return option.Nothing()

            mapping = typing.cast(
                "dict[typing.Any, typing.Any]",
                data,
            )

            fields: dict[str, Type] = {}

            for key, value in mapping.items():
                if type(key) is not str:
                    return option.Nothing()

                value_python_type: type = type(value)
                value_type_maybe = from_python_type(value_python_type)

                if isinstance(value_type_maybe, option.Nothing):
                    return option.Nothing()

                fields[key] = value_type_maybe.unwrap()

            return option.Some(Section(fields))

    # any other type does not have an equivalent
    return option.Nothing()


def to_python_type(ty: Type) -> type:  # noqa: PLR0911
    """
    Return the equivalent python type to `ty`.

    Note that this is a lossy transformation. Most notably,
    sections will be converted to plain dicts, which means that
    `from_python_type` cannot be used to recover `ty`.
    """

    match ty:
        case ScalarType.Never:
            return typing.cast("type", typing.Never)
        case ScalarType.String:
            return str
        case ScalarType.ProjectIdentifier:
            return str
        case ScalarType.CompilerName:
            # lossy! but datatypes.CompilerName is a TypeAliasType
            # (even if it was the Literal type it would still be useless)
            return str
        case List(item_type):
            item_python_type = to_python_type(item_type)
            return list[item_python_type]
        case Optional(item_type):
            item_python_type = to_python_type(item_type)
            return typing.cast("type", option.Option[item_python_type])
        case Section(fields):
            # pure laziness tbh, ideally it would return the dict
            # associated GenericAlias 😬
            return type(fields)


# TODO: write typechecking2.py
