"""Форматы документов, определение по расширению и вспомогательные карты.

Добавление нового формата = одна запись в ``Format`` + строки в картах ниже
(+ регистрация пары в ``backends/__init__.py``). Существующий код не трогается.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Union

from markforge.core.errors import UnknownFormatError


class Format(str, Enum):
    """Поддерживаемые форматы. Значение = каноническое имя формата."""

    MARKDOWN = "markdown"
    DOCX = "docx"
    EPUB = "epub"
    HTML = "html"
    PDF = "pdf"

    @property
    def title(self) -> str:
        return _TITLES[self]


# Человекочитаемые названия (для интерфейсов).
_TITLES: dict[Format, str] = {
    Format.MARKDOWN: "Markdown",
    Format.DOCX: "Word (DOCX)",
    Format.EPUB: "EPUB",
    Format.HTML: "HTML",
    Format.PDF: "PDF",
}

# Расширение файла -> формат.
_EXT_MAP: dict[str, Format] = {
    ".md": Format.MARKDOWN,
    ".markdown": Format.MARKDOWN,
    ".mdown": Format.MARKDOWN,
    ".mkd": Format.MARKDOWN,
    ".mdtext": Format.MARKDOWN,
    ".docx": Format.DOCX,
    ".epub": Format.EPUB,
    ".html": Format.HTML,
    ".htm": Format.HTML,
    ".xhtml": Format.HTML,
    ".pdf": Format.PDF,
}

# Формат -> каноническое расширение выходного файла.
CANONICAL_EXT: dict[Format, str] = {
    Format.MARKDOWN: ".md",
    Format.DOCX: ".docx",
    Format.EPUB: ".epub",
    Format.HTML: ".html",
    Format.PDF: ".pdf",
}

# Форматы, из которых нельзя конвертировать (только как цель).
OUTPUT_ONLY: frozenset[Format] = frozenset({Format.PDF})

# Все расширения, которые программа умеет открывать (для диалогов выбора файла).
INPUT_EXTENSIONS: tuple[str, ...] = tuple(
    ext for ext, fmt in _EXT_MAP.items() if fmt not in OUTPUT_ONLY
)


def detect_format(path: Union[str, Path]) -> Format:
    """Определить формат по расширению файла."""
    ext = Path(path).suffix.lower()
    try:
        return _EXT_MAP[ext]
    except KeyError:
        known = ", ".join(sorted(_EXT_MAP))
        raise UnknownFormatError(
            f"Не удалось определить формат по расширению {ext!r}. "
            f"Известные расширения: {known}"
        ) from None


def coerce_format(value: Union[Format, str]) -> Format:
    """Привести строку/enum к ``Format``."""
    if isinstance(value, Format):
        return value
    try:
        return Format(str(value).lower().lstrip("."))
    except ValueError:
        # Разрешаем передавать расширение вроде ".docx" или "docx".
        ext = "." + str(value).lower().lstrip(".")
        if ext in _EXT_MAP:
            return _EXT_MAP[ext]
        raise UnknownFormatError(f"Неизвестный формат: {value!r}") from None


def canonical_ext(fmt: Format) -> str:
    return CANONICAL_EXT[fmt]
