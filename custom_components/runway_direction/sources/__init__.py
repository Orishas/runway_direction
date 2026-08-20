"""Forecast sources for the Runway Direction integration."""

from .base import RunwaySource
from .brp import BrpSource
from .rwdf import RwdfSource

SOURCES: tuple[RunwaySource, ...] = (RwdfSource(), BrpSource())

__all__ = ["SOURCES", "BrpSource", "RunwaySource", "RwdfSource"]
