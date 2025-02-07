"""
ulna's configuration file scheme.
"""

from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from . import datatypes


class ProgramSectionScheme(typing.TypedDict, total=False):
    """
    Typed interface for a valid program section.
    """

    name: typing.Required[str]
    description: str


class DependenciesSectionScheme(typing.TypedDict, total=False):
    """
    Typed interface for a valid dependencies section.
    """

    include_dirs: list[str]
    include_shared: list[str]


class BuildSectionScheme(typing.TypedDict, total=False):
    """
    Typed interface for a valid build section.
    """

    compiler: datatypes.CompilerName
    additional_flags: list[str]


class ConfigurationScheme(typing.TypedDict, total=False):
    """
    Typed interface for a valid configuration file.
    """

    program: typing.Required[ProgramSectionScheme]
    dependencies: DependenciesSectionScheme
    build: BuildSectionScheme
