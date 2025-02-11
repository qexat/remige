"""
ulna's CLI.
"""

from __future__ import annotations

import argparse
import os
import sys
import typing

import result

from ulna import typesys_old

from . import builder
from . import config
from . import datatypes
from . import logger

BUILD_MODE_OPTIONS: set[datatypes.BuildMode] = {"development", "release"}
BUILD_MODE_DEFAULT: datatypes.BuildMode = "development"


class App:
    """
    Instance of the ulna build system.
    """

    def __init__(self, namespace: datatypes.UlnaNamespace) -> None:
        self.logger: typing.Final = logger.Logger(
            verbose=namespace.verbose,
        )
        self.build_mode: typing.Final = namespace.mode

    def run(self) -> int:
        """
        Run the instance.

        Return 0 upon success, and 1 upon failure.
        """

        venv_path = os.environ.get("VIRTUAL_ENV")

        if venv_path is None:
            self.logger.error("no virtual environment detected")
            return 1

        config_path = "ulna-project.toml"

        match config.load_toml(config_path):
            case result.Err(error):
                self.logger.error(error.render_message())

                return 1
            case result.Ok(toml_data):
                pass  # awkward

        self.logger.info("EXPERIMENTAL: type-checking based validation")

        if typesys_old.Config.check(toml_data):
            self.logger.info("type-checking passed")
        else:
            self.logger.info("type-checking failed")

        match config.validate(toml_data):  # pyright: ignore[reportArgumentType]
            case result.Err(errors):
                for error in errors:
                    self.logger.error(error.render_message())

                return 1
            case result.Ok(_config_):
                pass  # awkward

        project_builder = builder.Builder(
            self.logger,
            config=_config_,
            binary_dir=f"{venv_path}/bin",
        )

        succeeded = project_builder.build(mode=self.build_mode)

        return 0 if succeeded else 1


def build_parser() -> argparse.ArgumentParser:
    """
    Build the argument parser used for the CLI.
    """

    common_arguments = argparse.ArgumentParser(add_help=False)

    _ = common_arguments.add_argument(
        "--verbose",
        action="store_true",
        help="shows more detailed output",
    )

    parser = argparse.ArgumentParser(allow_abbrev=False)

    subparsers = parser.add_subparsers(dest="command", required=True)

    build_subparser = subparsers.add_parser(
        "build",
        description="build the C project",
        parents=[common_arguments],
    )

    _ = build_subparser.add_argument(
        "--mode",
        choices=BUILD_MODE_OPTIONS,
        default=BUILD_MODE_DEFAULT,
        help="optimizes for performance or for debugging",
    )

    return parser


def main(args: list[str] | None = None) -> int:
    """
    Entry point of ulna's CLI.
    """

    if args is None:
        args = sys.argv[1:]

    parser = build_parser()
    namespace = typing.cast(
        "datatypes.UlnaNamespace",
        parser.parse_args(args),
    )

    return App(namespace).run()


if __name__ == "__main__":
    raise SystemExit(main())
