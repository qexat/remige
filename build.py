#!/usr/bin/env python3

"""
Script to build Remige.
"""

from __future__ import annotations

import abc
import argparse
import os
import subprocess
import sys
import textwrap
import typing

import anstrip

if typing.TYPE_CHECKING:
    import _typeshed

PROGRAM_NAME = "remige"
DEPENDENCIES: list[str] = []
ADDITIONAL_FLAGS: list[str] = []


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
        "--compiler",
        choices=COMPILER_OPTIONS,
        default=COMPILER_DEFAULT,
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
    compiler: CompilerName
    verbose: bool


class BuildLogger:
    """
    Logger of the build script.
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

    def error_verbose(
        self,
        message: str,
        *,
        fallback_hint: str | None = None,
    ) -> None:
        """
        Log an error if the verbose mode is on.
        """

        if self.verbose:
            self.error(message)
        elif fallback_hint is not None:
            self.hint(fallback_hint)

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

        for line in message.splitlines():
            anstrip.print(self._make_line("info", 4, line), file=self.out)

    def hint(self, message: str) -> None:
        """
        Log a hint.
        """

        for line in message.splitlines():
            anstrip.print(self._make_line("hint", 5, line), file=self.out)


def build(options: BuildOptions) -> int:
    """
    Core function to build Remige.
    """

    logger = BuildLogger(verbose=options.verbose)
    venv_path = os.environ.get("VIRTUAL_ENV")

    if venv_path is None:
        logger.error("no virtual environment detected")
        return 1

    compiler = COMPILER_OPTIONS[options.compiler]
    command = compiler.generate_command(
        "program",
        PROGRAM_NAME,
        mode=options.mode,
        binary_dir=venv_path,
        dependencies=DEPENDENCIES,
        additional_flags=ADDITIONAL_FLAGS,
    )

    if options.verbose:
        logger.info(command)

    completed = subprocess.run(  # noqa: S603
        command.split(),
        capture_output=True,
        check=False,
    )

    if completed.returncode != 0:
        logger.error("Remige failed to build")

        hint = f"Pass --verbose to show {options.compiler}'s output"
        logger.error_verbose(
            textwrap.indent(completed.stderr.decode(), "| "),
            fallback_hint=hint,
        )

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
