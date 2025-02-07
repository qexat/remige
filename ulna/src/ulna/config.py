"""
Various utilities to load and validate ulna's configuration
file.
"""

from __future__ import annotations

import dataclasses

import result
import tomllib

from . import predicates
from . import scheme
from . import validator


@dataclasses.dataclass(frozen=True)
class ConfigFileNotFoundError:
    """
    Error when the configuration file does not exist.
    """


@dataclasses.dataclass(frozen=True)
class ConfigFilePermissionError:
    """
    Error when the configuration file does not have read
    permissions.
    """


@dataclasses.dataclass(frozen=True)
class MalformedTOMLError:
    """
    Error when the configuration file's TOML is malformed.
    """


@dataclasses.dataclass(slots=True, frozen=True)
class InvalidConfigFileError:
    """
    Error when the configuration file does not follow the
    scheme.
    """

    field_name: str
    message: str


type LoadError = (
    ConfigFileNotFoundError
    | ConfigFilePermissionError
    | MalformedTOMLError
    | InvalidConfigFileError
)


def get_error_message(path: str, error: LoadError) -> str:
    """
    Generate the error message given the `path` of the invalid
    configuration file and its `error` data.
    """

    match error:
        case ConfigFileNotFoundError():
            return f"file {path!r} could not be found"
        case ConfigFilePermissionError():
            return f"file {path!r} cannot be read (missing permissions)"
        case MalformedTOMLError():
            return f"file {path!r} is not valid TOML"
        case InvalidConfigFileError(field_name, message):
            return (
                f"file {path!r} is an invalid configuration\n"
                f"  {field_name}: {message}"
            )


PROGRAM_SECTION_VALIDATOR = (
    validator.Builder()
    .add_field("name", predicates.is_project_identifier)
    .add_field("description", predicates.is_string, optional=True)
    .build(for_type=scheme.ProgramSectionScheme)
)

DEPENDENCIES_SECTION_VALIDATOR = (
    validator.Builder()
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
    validator.Builder()
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
    .add_field("program", PROGRAM_SECTION_VALIDATOR.validate)
    .add_field(
        "dependencies",
        DEPENDENCIES_SECTION_VALIDATOR.validate,
        optional=True,
    )
    .add_field("build", BUILD_SECTION_VALIDATOR.validate, optional=True)
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
        return result.Err(ConfigFileNotFoundError())

    try:
        with file:
            raw_contents = file.read()
    except PermissionError:
        return result.Err(ConfigFilePermissionError())

    try:
        config = tomllib.loads(raw_contents)
    except tomllib.TOMLDecodeError:
        return result.Err(MalformedTOMLError())

    if not CONFIG_VALIDATOR.validate(config):
        # TODO: refine error message
        return result.Err(
            InvalidConfigFileError(
                "unknown",
                "invalid field",
            )
        )

    return result.Ok(config)
