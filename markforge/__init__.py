"""MarkForge — универсальный конвертер документов.

Публичный API:

    from markforge import convert, Format, ConvertOptions

    result = convert("book.md", Format.EPUB)
    print(result.output_path)

Ядро (`markforge.core`) не зависит от интерфейса и используется одинаково
из CLI, оконного приложения (GUI) и HTTP-сервиса (мост для мобильного
приложения).
"""

from __future__ import annotations

from markforge.core.engine import convert
from markforge.core.formats import Format, detect_format
from markforge.core.options import ConvertOptions, ConvertResult, EpubMetadata
from markforge.core.errors import (
    MarkForgeError,
    UnknownFormatError,
    UnsupportedConversionError,
    BackendUnavailableError,
    ConversionFailedError,
    CorruptInputError,
)

__version__ = "0.1.0"
__all__ = [
    "convert",
    "Format",
    "detect_format",
    "ConvertOptions",
    "ConvertResult",
    "EpubMetadata",
    "MarkForgeError",
    "UnknownFormatError",
    "UnsupportedConversionError",
    "BackendUnavailableError",
    "ConversionFailedError",
    "CorruptInputError",
    "__version__",
]
