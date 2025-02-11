"""
Ulna types.
"""

from __future__ import annotations

import typing

from ulna import predicates

from . import typechecking


def _specialize_list_type[PyTypeT](
    name: str,
    item_type: typechecking.Type[PyTypeT],
) -> typechecking.Type[list[PyTypeT]]:
    specialized_name = f"{name}({item_type.name})"

    return typechecking.Type(
        specialized_name,
        typechecking.make_list_checker(
            specialized_name,
            item_type=item_type,
        ),
    )


String: typing.Final = typechecking.Type.from_predicate(
    "String",
    predicates.is_string,
)

ProjectIdentifier: typing.Final = typechecking.Type.from_predicate(
    "ProjectIdentifier",
    predicates.is_project_identifier,
)

CompilerName: typing.Final = typechecking.Type.from_predicate(
    "CompilerName",
    predicates.is_compiler_name,
)

List: typing.Final = typechecking.TypeFunctor(
    "List",
    _specialize_list_type,
)
