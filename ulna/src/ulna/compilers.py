"""
Supported compilers and their command generation implementation.
"""

from __future__ import annotations

import typing

from . import datatypes


class GCC(datatypes.Compiler):
    """
    The GCC compiler.
    """

    name = "gcc"
    _base_flags: typing.Final = " -Wall -Wextra "

    @typing.override
    def get_build_mode_flags(self, mode: datatypes.BuildMode) -> str:
        match mode:
            case "development":
                return self._base_flags + (
                    " -O0 -g2 -Wpedantic -Werror "
                    " -fsanitize=undefined,address "
                )
            case "release":
                return (
                    self._base_flags + " -O2 -march=native -mtune=native "
                )

    @typing.override
    def get_source_kind_arguments(
        self,
        kind: datatypes.SourceKind,
        source_name: str,
        binary_dir: str,
    ) -> str:
        match kind:
            case "library":
                return f" -c -o {source_name}.o "
            case "program":
                return f" -o {binary_dir}/{source_name} "


OPTIONS: dict[datatypes.CompilerName, datatypes.Compiler] = {
    "gcc": GCC(),
}

DEFAULT: datatypes.CompilerName = "gcc"
