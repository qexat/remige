"""
ulna configuration format type system
"""

from __future__ import annotations

import dataclasses
import typing

from . import predicates
from . import scheme


@dataclasses.dataclass(slots=True, frozen=True)
class Type[T]:
    """
    Type of ulna configuration format types.
    """

    check: typing.Callable[[typing.Any | None], typing.TypeGuard[T]]


def make_list_type[T](ty: Type[T]) -> Type[list[T]]:
    """
    Create a list type where items are of the type `ty`.
    """

    def is_any_list(
        data: typing.Any | None,
    ) -> typing.TypeGuard[list[typing.Any]]:
        return isinstance(data, list)

    def list_check(data: typing.Any | None) -> typing.TypeGuard[list[T]]:
        if not is_any_list(data):
            return False

        return all(ty.check(item) for item in data)

    return Type(list_check)


def make_optional_type[T](ty: Type[T]) -> Type[T]:
    """
    Create an optional type given `ty`.
    """

    def optional_check(data: typing.Any | None) -> typing.TypeGuard[T]:
        if data is None:
            return True

        return ty.check(data)

    return Type(optional_check)


def make_section_type[T](
    representing: type[T],  # noqa: ARG001
    **fields: Type[typing.Any],
) -> Type[T]:
    """
    Create a section type given its `fields`.
    """

    def _is_any_section(
        data: typing.Any | None,
    ) -> typing.TypeGuard[dict[typing.Any, typing.Any]]:
        return isinstance(data, dict)

    def section_check(data: typing.Any | None) -> typing.TypeGuard[T]:
        if not _is_any_section(data):
            return False

        seen_fields: set[str] = set()

        for name, ty in fields.items():
            if not ty.check(data.get(name)):
                return False

            seen_fields.add(name)

        extraneous_fields = {key for key in data if key not in seen_fields}

        return not extraneous_fields

    return Type(section_check)


CompilerName: typing.Final = Type(predicates.is_compiler_name)
Identifier: typing.Final = Type(predicates.is_project_identifier)
String: typing.Final = Type(predicates.is_string)

List: typing.Final = make_list_type
Optional: typing.Final = make_optional_type
Section: typing.Final = make_section_type

ProgramSection = Section(
    scheme.ProgramSectionScheme,
    name=String,
    description=Optional(String),
)

DependenciesSection = Section(
    scheme.DependenciesSectionScheme,
    include_dirs=Optional(List(String)),
    include_shared=Optional(List(String)),
)

BuildSection = Section(
    scheme.BuildSectionScheme,
    compiler=Optional(CompilerName),
    additional_flags=Optional(List(String)),
)

Config = Section(
    scheme.ConfigurationScheme,
    program=ProgramSection,
    dependencies=Optional(DependenciesSection),
    build=Optional(BuildSection),
)
