"""
Core of ulna.
"""

# ruff: noqa: S603 - we generate the subprocess command ourselves
# ruff: noqa: G004 - we are not using the built-in logger

from __future__ import annotations

import contextlib
import os
import subprocess
import textwrap
import typing

from . import compilers

if typing.TYPE_CHECKING:
    from . import datatypes
    from . import logger
    from . import scheme


class Builder:
    """
    Core component of the build system.
    It is what builds a given project.
    """

    def __init__(
        self,
        logger: logger.Logger,
        *,
        config: scheme.ConfigurationScheme,
        binary_dir: str,
    ) -> None:
        self.logger: typing.Final = logger

        # *- program data -* #

        self.program_name: typing.Final = config["program"]["name"]
        self.binary_dir: typing.Final = binary_dir

        self.dependencies: typing.Final = config.get("dependencies", {})
        self.included_dirs: typing.Final = self.dependencies.get(
            "include_dirs",
            [],
        )
        self.included_shared_objects: typing.Final = self.dependencies.get(
            "include_shared",
            [],
        )

        self.build_options: typing.Final = config.get("build", {})
        self.compiler_name: typing.Final = self.build_options.get(
            "compiler",
            compilers.DEFAULT,
        )
        self.additional_flags: typing.Final = self.build_options.get(
            "additional_flags",
            [],
        )

    def build(self, *, mode: datatypes.BuildMode) -> bool:
        """
        Perform the project build.

        Return `True` on success, `False` on failure.
        """

        compiler = compilers.OPTIONS[self.compiler_name]

        command = compiler.generate_command(
            "program",
            self.program_name,
            mode=mode,
            binary_dir=self.binary_dir,
            dependencies=self.included_shared_objects,
            additional_flags=self.additional_flags,
        )

        self.logger.info(command)

        completed_process = subprocess.run(
            command.split(),
            capture_output=True,
            check=False,
        )

        if completed_process.returncode != 0:
            self.logger.error(f"{self.program_name} failed to build")
            self.logger.error(
                # e.g. gcc: <gcc error message>
                textwrap.indent(
                    completed_process.stderr.decode(),
                    f"{self.compiler_name}: ",
                )
            )

            self.delete_binary()

            return False

        return True

    def delete_binary(self) -> None:
        """
        Remove the binary.

        This method is called upon build failure.
        """

        with contextlib.suppress(OSError):
            os.remove(f"{self.binary_dir}/{self.program_name}")
