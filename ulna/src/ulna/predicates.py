"""
Various simple predicates used in validators.
"""

from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from . import datatypes


def is_string(value: typing.Any) -> typing.TypeGuard[str]:
    """
    Determine whether `value` is a string.
    """

    return isinstance(value, str)


def is_list_of[ItemT](
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


def is_list_of_strings(
    value: typing.Any,
) -> typing.TypeGuard[list[str]]:
    """
    Determine whether `value` is a list of strings.
    """

    return is_list_of(value, item_type=str)


def is_any_dict(
    value: typing.Any,
) -> typing.TypeGuard[dict[typing.Any, typing.Any]]:
    """
    Determine whether `value` is some dictionary with arbitrary
    key and value types.
    """

    return isinstance(value, dict)


def is_project_identifier(value: typing.Any) -> typing.TypeGuard[str]:
    """
    Determine whether `value` is a project identifier.
    """

    # TODO: use my own identifier conventions
    return isinstance(value, str) and value.isidentifier()


def is_compiler_name(
    value: typing.Any,
) -> typing.TypeGuard[datatypes.CompilerName]:
    """
    Determine whether `value` is a compiler name.
    """

    return value == "gcc"
