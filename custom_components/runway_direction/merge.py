"""Combining forecasts from several sources.

Sources overlap in time and differ in quality: the worldwide source resolves a
single runway over two days, the German/Austrian one only an axis but over
five. Rather than picking one, the better source wins wherever it has data and
the weaker one extends beyond it — with every slot keeping its own source, so
a mixed forecast stays readable.
"""

from __future__ import annotations

from dataclasses import replace

from .models import RunwaySlot, SourceResult


def merge_results(results: tuple[SourceResult, ...] | list[SourceResult]) -> tuple[RunwaySlot, ...]:
    """Merge source results into one gap-free-where-known timeline."""
    merged: list[RunwaySlot] = []
    for result in results:
        if not result.ok:
            continue
        for slot in result.slots:
            merged.extend(_uncovered(slot, merged))
        merged.sort(key=lambda item: item.start)
    return tuple(merged)


def _uncovered(slot: RunwaySlot, existing: list[RunwaySlot]) -> list[RunwaySlot]:
    """Return the parts of a slot no earlier source already covers."""
    pieces = [slot]
    for other in existing:
        remaining: list[RunwaySlot] = []
        for piece in pieces:
            remaining.extend(_subtract(piece, other))
        pieces = remaining
        if not pieces:
            break
    return pieces


def _subtract(slot: RunwaySlot, other: RunwaySlot) -> list[RunwaySlot]:
    """Return slot minus the period covered by other."""
    if other.end <= slot.start or other.start >= slot.end:
        return [slot]

    pieces: list[RunwaySlot] = []
    if slot.start < other.start:
        pieces.append(replace(slot, end=other.start))
    if other.end < slot.end:
        pieces.append(replace(slot, start=other.end))
    return pieces
