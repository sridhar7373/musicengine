"""Small terminal helpers for quiet, color-aware command output."""

from __future__ import annotations

import os
import sys
import time
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
        self._download_label = ""
        self._download_started = 0.0
        self._download_last_render = 0.0

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

    @staticmethod
    def _size(value: int) -> str:
        if value >= 1024 * 1024:
            return f"{value / (1024 * 1024):.1f} MB"
        if value >= 1024:
            return f"{value / 1024:.0f} KB"
        return f"{value} B"

    @staticmethod
    def _speed(value: float) -> str:
        if value >= 1024 * 1024:
            return f"{value / (1024 * 1024):.1f} MB/s"
        if value >= 1024:
            return f"{value / 1024:.0f} KB/s"
        return f"{value:.0f} B/s"

    def start_download(self, label: str) -> None:
        self.end_progress()
        self._download_label = label
        self._download_started = time.monotonic()
        self._download_last_render = 0.0

    def download_progress(self, received: int, total: int | None) -> None:
        if not self.is_tty:
            return
        now = time.monotonic()
        if now - self._download_last_render < 0.12:
            return
        elapsed = max(now - self._download_started, 0.001)
        speed = received / elapsed
        details = f"{self._size(received)} · {self._speed(speed)}"
        if total:
            width = 14
            filled = min(width, round(width * received / total))
            bar = self.paint("█" * filled, "cyan") + self.paint(
                "░" * (width - filled), "dim"
            )
            percent = min(100, received * 100 // total)
            details = f"{bar} {percent:3d}% · {details}"
        self.stream.write(f"\r{self._download_label} {details}\033[K")
        self.stream.flush()
        self._progress_active = True
        self._download_last_render = now

    def finish_download(self, size: int) -> None:
        elapsed = max(time.monotonic() - self._download_started, 0.001)
        details = f"{self._size(size)} · {self._speed(size / elapsed)}"
        if self.is_tty:
            self._download_last_render = 0.0
            self.download_progress(size, size)
            self.end_progress()
        else:
            self.line(f"✓ {self._download_label} · {details}")
