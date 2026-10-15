"""Ядро конвертации MarkForge — независимое от интерфейса."""

from __future__ import annotations

from markforge.core.engine import convert
from markforge.core.formats import Format, detect_format, CANONICAL_EXT
from markforge.core.options import ConvertOptions, ConvertResult, EpubMetadata
from markforge.core.registry import REGISTRY

__all__ = [
    "convert",
    "Format",
    "detect_format",
    "CANONICAL_EXT",
    "ConvertOptions",
    "ConvertResult",
    "EpubMetadata",
    "REGISTRY",
]
