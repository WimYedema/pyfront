from collections.abc import Iterable
from typing import Any, TypeVar

T = TypeVar("T")


def stabilizing_1d[T](check: dict[T, bool]) -> Iterable[dict[T, bool]]:
    """Yield the dict until it stabilizes (no more changes)."""
    old_values = None
    while True:
        new_values = {key for key, value in check.items() if value}
        if new_values != old_values:
            old_values = new_values
            yield check
        else:
            break


def stabilize_2d[T](check: dict[Any, set[T]]) -> Iterable[dict[Any, set[T]]]:
    """Yield the dict until it stabilizes (no more changes)."""
    old_lens = None
    while True:
        new_lens = {key: len(value) for key, value in check.items()}
        if new_lens != old_lens:
            old_lens = new_lens
            yield check
        else:
            break
