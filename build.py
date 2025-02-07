#!/usr/bin/env python3

"""
Script to build Remige.
"""

from __future__ import annotations

import abc
import argparse
import contextlib
import os
import subprocess
import sys
import textwrap
import typing

import anstrip
import tomllib

if typing.TYPE_CHECKING:
    import collections.abc

    import _typeshed


class _ProgramSection(typing.TypedDict, total=False):
    name: typing.Required[str]
    description: str


class _DependenciesSection(typing.TypedDict, total=False):
    include_dirs: list[str]
    exclude_dirs: list[str]
    include_headers: list[str]
    include_shared: list[str]


class _BuildSection(typing.TypedDict, total=False):
    compiler: CompilerName
    additional_flags: list[str]


class ConfigScheme(typing.TypedDict, total=False):
    """
    Typed interface for a valid configuration file.
    """

    program: typing.Required[_ProgramSection]
    dependencies: _DependenciesSection
    build: _BuildSection


class ValidationField(typing.NamedTuple):
    """
    Represents a TOML field to validate.
    """

    name: str
    validator: typing.Callable[[typing.Any], bool]
    optional: bool


class Validator[T]:
    """
    Handles validation of the `T` node given a dumb value,
    usually extracted from parsing the TOML config file.
    """

    def __init__(
        self,
        fields: collections.abc.Iterable[ValidationField],
        *,
        for_type: type[T],
    ) -> None:
        self._fields = fields
        self._for_type = for_type

    @staticmethod
    def _check_field(
        field: typing.Any | None,
        validator: typing.Callable[[typing.Any], bool],
        *,
        optional: bool = False,
    ) -> bool:
        if field is None:
            return optional

        return validator(field)

    def validate(self, value: typing.Any) -> typing.TypeGuard[T]:
        """
        Return whether `value` is a valid `T` node.
        """

        if not _is_any_dict(value):
            return False

        for field in self._fields:
            if not self._check_field(
                value.get(field.name),
                field.validator,
                optional=field.optional,
            ):
                return False

        return True


class ValidatorBuilder:
    """
    Builder for a node validator.

    Each method returns the builder so it can be chained.
    """

    def __init__(self) -> None:
        self._fields: list[ValidationField] = []

    def _add_field(
        self,
        name: str,
        validator: typing.Callable[[typing.Any], bool],
        *,
        optional: bool,
    ) -> None:
        self._fields.append(
            ValidationField(
                name,
                validator,
                optional=optional,
            )
        )

    def add_field(
        self,
        name: str,
        validator: typing.Callable[[typing.Any], bool],
        *,
        optional: bool = False,
    ) -> typing.Self:
        """
        Add a validation field given its `name`, a `validator`
        function that verifies that the field itself is valid,
        and whether it is `optional` or not.
        """

        self._add_field(name, validator, optional=optional)

        return self

    def build[T](self, *, for_type: type[T]) -> Validator[T]:
        """
        Construct the node validator for the type `T` and return
        it.

        This cannot be enforced, but `T` should be a subclass of
        `typing.TypedDict`.
        """

        return Validator(self._fields, for_type=for_type)


def _is_identifier(value: typing.Any) -> typing.TypeGuard[str]:
    return isinstance(value, str) and value.isidentifier()


def _is_string(value: typing.Any) -> typing.TypeGuard[str]:
    return isinstance(value, str)


def _is_list_of[ItemT](
    value: typing.Any,
    *,
    item_type: type[ItemT],
) -> typing.TypeGuard[list[ItemT]]:
    return isinstance(value, list) and all(
        isinstance(item, item_type)
        for item in typing.cast("list[typing.Any]", value)
    )


def _is_list_of_strings(
    value: typing.Any,
) -> typing.TypeGuard[list[str]]:
    return _is_list_of(value, item_type=str)


def _is_any_dict(
    value: typing.Any,
) -> typing.TypeGuard[dict[typing.Any, typing.Any]]:
    return isinstance(value, dict)


def _is_valid_compiler_name(
    value: typing.Any,
) -> typing.TypeGuard[CompilerName]:
    return value == "gcc"


PROGRAM_SECTION_VALIDATOR = (
    ValidatorBuilder()
    .add_field("name", _is_identifier)
    .add_field("description", _is_string, optional=True)
    .build(for_type=_ProgramSection)
)
DEPENDENCIES_SECTION_VALIDATOR = (
    ValidatorBuilder()
    .add_field("include_dirs", _is_list_of_strings, optional=True)
    .add_field("exclude_dirs", _is_list_of_strings, optional=True)
    .add_field("include_shared", _is_list_of_strings, optional=True)
    .build(for_type=_DependenciesSection)
)
BUILD_SECTION_VALIDATOR = (
    ValidatorBuilder()
    .add_field("compiler", _is_valid_compiler_name, optional=True)
    .add_field("additional_flags", _is_list_of_strings, optional=True)
    .build(for_type=_BuildSection)
)
CONFIG_VALIDATOR = (
    ValidatorBuilder()
    .add_field("program", PROGRAM_SECTION_VALIDATOR.validate)
    .add_field(
        "dependencies",
        DEPENDENCIES_SECTION_VALIDATOR.validate,
        optional=True,
    )
    .add_field("build", BUILD_SECTION_VALIDATOR.validate, optional=True)
    .build(for_type=ConfigScheme)
)


class Compiler(abc.ABC):
    """
    Represents a C compiler (e.g. GCC).
    """

    name: typing.ClassVar[str]

    @abc.abstractmethod
    def get_build_mode_flags(self, mode: BuildMode) -> str:
        """
        Return a string of the flags for the given build `mode`.
        """

    @abc.abstractmethod
    def get_source_kind_arguments(
        self,
        kind: SourceKind,
        source_name: str,
        binary_dir: str,
    ) -> str:
        """
        Return a string of the flags given a `source_name` and
        its `kind`.
        """

    def generate_command(  # noqa: PLR0913
        self,
        kind: SourceKind,
        source_name: str,
        *,
        mode: BuildMode,
        binary_dir: str,
        dependencies: list[str] | None = None,
        additional_flags: list[str] | None = None,
    ) -> str:
        """
        Generate a shell command to build `source_name` using the compiler.
        """

        if dependencies is None:
            dependencies = []

        if additional_flags is None:
            additional_flags = []

        template = (
            "{name} {task} {source_name}.c {object_files} "
            "{build_mode_flags} {additional_flags}"
        )

        task = self.get_source_kind_arguments(
            kind,
            source_name,
            binary_dir,
        )
        object_files = " ".join(
            file if file.endswith(".o") else file + ".o"
            for file in dependencies
        )
        build_mode_flags = self.get_build_mode_flags(mode)
        _additional_flags_ = " ".join(additional_flags)

        return template.format(
            name=self.name,
            task=task,
            source_name=source_name,
            object_files=object_files,
            build_mode_flags=build_mode_flags,
            additional_flags=_additional_flags_,
        )


class GCC(Compiler):
    """
    The GCC compiler.
    """

    name = "gcc"

    @typing.override
    def get_build_mode_flags(self, mode: BuildMode) -> str:
        base = "-Wall -Wextra "

        match mode:
            case "development":
                return base + (
                    "-O0 -g2 -Wpedantic -Werror "
                    "-fsanitize=undefined,address"
                )
            case "release":
                return base + "-O2 -march=native -mtune=native"

    @typing.override
    def get_source_kind_arguments(
        self,
        kind: SourceKind,
        source_name: str,
        binary_dir: str,
    ) -> str:
        match kind:
            case "library":
                return f"-c -o {source_name}.o"
            case "program":
                return f"-o {binary_dir}/{source_name}"


type BuildMode = typing.Literal["release", "development"]
type CompilerName = typing.Literal["gcc"]
type SourceKind = typing.Literal["program", "library"]

BUILD_MODE_OPTIONS: set[BuildMode] = {"development", "release"}
BUILD_MODE_DEFAULT: BuildMode = "development"

COMPILER_OPTIONS: dict[CompilerName, Compiler] = {"gcc": GCC()}
COMPILER_DEFAULT: CompilerName = "gcc"


def create_parser() -> argparse.ArgumentParser:
    """
    Build the argument parser used for the CLI.
    """

    parser = argparse.ArgumentParser()

    _ = parser.add_argument(
        "--mode",
        choices=BUILD_MODE_OPTIONS,
        default=BUILD_MODE_DEFAULT,
    )

    _ = parser.add_argument(
        "--verbose",
        action="store_true",
    )

    return parser


class BuildOptions(typing.Protocol):
    """
    Record representing the build options.
    """

    mode: BuildMode
    verbose: bool


class BuildLogger:
    """
    Logger of Ulna.
    """

    def __init__(
        self,
        *,
        out: _typeshed.SupportsWrite[str] | None = None,
        err: _typeshed.SupportsWrite[str] | None = None,
        verbose: bool,
    ) -> None:
        self.out: typing.Any = sys.stdout if out is None else out
        self.err: typing.Any = sys.stderr if err is None else err
        self.verbose = verbose

    @staticmethod
    def _make_line(
        label: str,
        color: typing.Literal[1, 3, 4, 5],
        line: str,
    ) -> str:
        return f"\x1b[1;3{color}m{label.title()}:\x1b[22;39m\t{line}"

    def error(self, message: str) -> None:
        """
        Log an error.
        """

        for line in message.splitlines():
            anstrip.print(self._make_line("error", 1, line), file=self.err)

    def warn(self, message: str) -> None:
        """
        Log a warning.
        """

        for line in message.splitlines():
            anstrip.print(
                self._make_line("warning", 3, line),
                file=self.err,
            )

    def info(self, message: str) -> None:
        """
        Log some information.
        """

        if not self.verbose:
            return

        for line in message.splitlines():
            anstrip.print(self._make_line("info", 4, line), file=self.out)

    def hint(self, message: str) -> None:
        """
        Log a hint.
        """

        for line in message.splitlines():
            anstrip.print(self._make_line("hint", 5, line), file=self.out)


# TODO: this function does too much work
def read_config(path: str) -> ConfigScheme | None:
    """
    Read the config from `path` and validate it.
    """

    try:
        with open(path, "r", encoding="utf-8") as file:
            raw_contents = file.read()
    except OSError:
        return None

    try:
        config = tomllib.loads(raw_contents)
    except tomllib.TOMLDecodeError:
        return None

    if not CONFIG_VALIDATOR.validate(config):
        return None

    return config


# XXX: this function has a confusing job
def clean(program_name: str, path: str) -> None:
    """
    Clean artifacts and binaries upon build failure.
    """

    with contextlib.suppress(OSError):
        os.remove(f"{path}/{program_name}")


# TODO: this function does too much work
# TODO: make it a class
def build(options: BuildOptions) -> int:
    """
    Core function to build Remige.
    """

    logger = BuildLogger(verbose=options.verbose)
    venv_path = os.environ.get("VIRTUAL_ENV")

    if venv_path is None:
        logger.error("no virtual environment detected")
        return 1

    config = read_config("project.toml")

    if config is None:
        logger.error("configuration file is invalid or could not be found")
        return 1

    program_name = config["program"]["name"]
    binary_dir = f"{venv_path}/bin"

    # TODO: handle other dependencies as well
    dependencies = config.get("dependencies", {})
    shared_object_dependencies = dependencies.get("include_shared", [])

    build_options = config.get("build", {})
    compiler_name = build_options.get("compiler", COMPILER_DEFAULT)
    additional_flags = build_options.get("additional_flags", [])

    compiler = COMPILER_OPTIONS[compiler_name]
    command = compiler.generate_command(
        "program",
        program_name,
        mode=options.mode,
        binary_dir=binary_dir,
        dependencies=shared_object_dependencies,
        additional_flags=additional_flags,
    )

    logger.info(command)

    completed = subprocess.run(  # noqa: S603
        command.split(),
        capture_output=True,
        check=False,
    )

    if completed.returncode != 0:
        logger.error("Remige failed to build")
        logger.error(textwrap.indent(completed.stderr.decode(), "| "))

        clean(program_name, binary_dir)

        return 1

    return 0


def main(args: list[str]) -> int:
    """
    Entry point of the script.
    """

    parser = create_parser()

    return build(parser.parse_args(args))  # pyright: ignore[reportArgumentType]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
