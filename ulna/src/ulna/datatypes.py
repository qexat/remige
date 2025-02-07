"""
Shared datatypes used across ulna.
"""

from __future__ import annotations

import abc
import dataclasses
import typing


class AbstractError(abc.ABC):
    """
    Represents an error that can be rendered into a message.
    """

    @abc.abstractmethod
    def render_message(self) -> str:
        """
        Render the error into a printable message string.
        """


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


@dataclasses.dataclass(slots=True, frozen=True)
class Predicate[T]:
    """
    Function that checks if a value is of type `T`.
    """

    name: str
    function: typing.Callable[[typing.Any], typing.TypeGuard[T]]

    def __call__(self, value: typing.Any, /) -> typing.TypeGuard[T]:  # noqa: D102
        return self.function(value)


class UlnaNamespace(typing.Protocol):
    """
    Typed namespace of ulna's CLI arguments.
    """

    command: CommandName
    mode: BuildMode
    verbose: bool


type BuildMode = typing.Literal["release", "development"]
type CommandName = typing.Literal["build"]
type CompilerName = typing.Literal["gcc"]
type SourceKind = typing.Literal["program", "library"]
