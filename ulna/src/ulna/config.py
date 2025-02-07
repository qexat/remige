"""
Various utilities to load and validate ulna's configuration
file.
"""

from __future__ import annotations

import dataclasses
import typing

import result
import tomllib

from . import datatypes
from . import predicates
from . import scheme
from . import validator

# XXX: error handling is super smelly.
# TODO: make it nicer


@dataclasses.dataclass(frozen=True)
class ConfigFileNotFoundError(datatypes.AbstractError):
    """
    Error when the configuration file does not exist.
    """

    path: str

    @typing.override
    def render_message(self) -> str:
        return f"file {self.path!r} could not be found"


@dataclasses.dataclass(frozen=True)
class ConfigFilePermissionError(datatypes.AbstractError):
    """
    Error when the configuration file does not have read
    permissions.
    """

    path: str

    @typing.override
    def render_message(self) -> str:
        return f"file {self.path!r} cannot be read (missing permissions)"


@dataclasses.dataclass(frozen=True)
class MalformedTOMLError(datatypes.AbstractError):
    """
    Error when the configuration file's TOML is malformed.
    """

    path: str

    @typing.override
    def render_message(self) -> str:
        return f"file {self.path!r} is not valid TOML"


@dataclasses.dataclass(slots=True, frozen=True)
class InvalidConfigError:
    """
    Error when the configuration file is invalid.
    """

    errors: list[validator.ValidationError]


type LoadError = (
    ConfigFileNotFoundError
    | ConfigFilePermissionError
    | MalformedTOMLError
    | InvalidConfigError
)


def get_error_messages(error: LoadError) -> list[str]:
    """
    Generate the error message given the `path` of the invalid
    configuration file and its `error` data.
    """

    match error:
        case InvalidConfigError(errors):
            return [_error.render_message() for _error in errors]
        case _:
            return [error.render_message()]


PROGRAM_SECTION_VALIDATOR = (
    validator.Builder("program")
    .add_field("name", predicates.is_project_identifier)
    .add_field("description", predicates.is_string, optional=True)
    .build(for_type=scheme.ProgramSectionScheme)
)

DEPENDENCIES_SECTION_VALIDATOR = (
    validator.Builder("dependencies")
    .add_field(
        "include_dirs",
        predicates.is_list_of_strings,
        optional=True,
    )
    .add_field(
        "include_shared",
        predicates.is_list_of_strings,
        optional=True,
    )
    .build(for_type=scheme.DependenciesSectionScheme)
)

BUILD_SECTION_VALIDATOR = (
    validator.Builder("build")
    .add_field("compiler", predicates.is_compiler_name, optional=True)
    .add_field(
        "additional_flags",
        predicates.is_list_of_strings,
        optional=True,
    )
    .build(for_type=scheme.BuildSectionScheme)
)

CONFIG_VALIDATOR = (
    validator.Builder()
    .add_section(PROGRAM_SECTION_VALIDATOR)
    .add_section(DEPENDENCIES_SECTION_VALIDATOR, optional=True)
    .add_section(BUILD_SECTION_VALIDATOR, optional=True)
    .build(for_type=scheme.ConfigurationScheme)
)


def load(
    path: str,
) -> result.Result[scheme.ConfigurationScheme, LoadError]:
    """
    Read, load and validate the configuration file at the given
    `path`.
    """

    try:
        # we are using the context manager afterwards
        file = open(path, encoding="utf-8")  # noqa: SIM115
    except OSError:
        return result.Err(ConfigFileNotFoundError(path))

    try:
        with file:
            raw_contents = file.read()
    except PermissionError:
        return result.Err(ConfigFilePermissionError(path))

    try:
        config = tomllib.loads(raw_contents)
    except tomllib.TOMLDecodeError:
        return result.Err(MalformedTOMLError(path))

    return CONFIG_VALIDATOR.validate(config).map_err(InvalidConfigError)
