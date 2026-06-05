"""Small logging wrappers for report runtime messages."""

from __future__ import annotations


def log_message(message: str = "", *, end: str = "\n") -> None:
    print(message, end=end)
