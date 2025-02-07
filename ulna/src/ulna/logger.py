"""
ulna's simple logger.
"""

from __future__ import annotations

import sys
import typing

import anstrip

if typing.TYPE_CHECKING:
    import _typeshed


class Logger:
    """
    Logger of ulna.
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
