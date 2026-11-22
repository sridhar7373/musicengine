"""Small terminal helpers for quiet, color-aware command output."""

from __future__ import annotations

import os
import sys
from typing import TextIO


class Console:
    _COLORS = {
        "cyan": "36",
        "green": "32",
        "yellow": "33",
        "red": "31",
        "dim": "2",
        "bold": "1",
    }

    def __init__(self, no_color: bool = False):
        self.stream: TextIO = sys.stdout
        self.error_stream: TextIO = sys.stderr
        self.is_tty = self.stream.isatty()
        self.color_enabled = self.is_tty and not no_color and "NO_COLOR" not in os.environ
        self._progress_active = False

    def paint(self, value: str, *styles: str) -> str:
        if not self.color_enabled or not styles:
            return value
        codes = ";".join(self._COLORS[style] for style in styles)
        return f"\033[{codes}m{value}\033[0m"

    def line(self, value: str = "") -> None:
        print(value, file=self.stream)

    def error(self, value: str) -> None:
        self.end_progress()
        print(self.paint(f"✗ {value}", "red"), file=self.error_stream)

    def progress(self, label: str, current: int, total: int) -> None:
        if not self.is_tty:
            return
        width = 20
        filled = round(width * current / total) if total else width
        bar = self.paint("█" * filled, "cyan") + self.paint("░" * (width - filled), "dim")
        self.stream.write(f"\r{label} [{bar}] {current}/{total}\033[K")
        self.stream.flush()
        self._progress_active = True

    def end_progress(self) -> None:
        if self._progress_active:
            self.stream.write("\n")
            self.stream.flush()
            self._progress_active = False
