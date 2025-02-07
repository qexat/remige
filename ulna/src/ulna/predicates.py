"""
Various simple predicates used in validators.
"""

from __future__ import annotations

import typing

from . import datatypes


def make_predicate[T](
    name: str,
) -> typing.Callable[
    [typing.Callable[[typing.Any], typing.TypeGuard[T]]],
    datatypes.Predicate[T],
]:
    """
    Decorator to make a `Predicate` object.
    """

    return lambda function: datatypes.Predicate(name, function)


@make_predicate("string")
def is_string(value: typing.Any) -> typing.TypeGuard[str]:
    """
    Determine whether `value` is a string.
    """

    return isinstance(value, str)


def _is_list_of[ItemT](
    value: typing.Any,
    *,
    item_type: type[ItemT],
) -> typing.TypeGuard[list[ItemT]]:
    """
    Determine whether `value` is a list containing items of type
    `item_type`.
    """

    return isinstance(value, list) and all(
        isinstance(item, item_type)
        for item in typing.cast("list[typing.Any]", value)
    )


@make_predicate("list of strings")
def is_list_of_strings(
    value: typing.Any,
) -> typing.TypeGuard[list[str]]:
    """
    Determine whether `value` is a list of strings.
    """

    return _is_list_of(value, item_type=str)


def is_any_dict(
    value: typing.Any,
) -> typing.TypeGuard[dict[typing.Any, typing.Any]]:
    """
    Determine whether `value` is some dictionary with arbitrary
    key and value types.
    """

    return isinstance(value, dict)


def _is_identifier_particle(particle: str) -> bool:
    return all(
        "A" <= char <= "Z" or "a" <= char <= "z" or char == "_"
        for char in particle
    )


@make_predicate("project identifier")
def is_project_identifier(value: typing.Any) -> typing.TypeGuard[str]:
    """
    Determine whether `value` is a project identifier.
    """

    if not isinstance(value, str):
        return False

    particles = value.split("-")

    return all(_is_identifier_particle(particle) for particle in particles)


@make_predicate("compiler name")
def is_compiler_name(
    value: typing.Any,
) -> typing.TypeGuard[datatypes.CompilerName]:
    """
    Determine whether `value` is a compiler name.
    """

    return value == "gcc"
