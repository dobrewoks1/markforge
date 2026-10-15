"""Пресеты оформления: имя -> reference.docx / css.

Точка расширения: положите свой ``reference.docx`` (шаблон стилей Word) или
``.css`` в ``markforge/assets/presets/`` и добавьте запись в ``PRESETS``.
Пользовательские ``reference_doc``/``css`` в ``ConvertOptions`` имеют приоритет.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from markforge.core.options import ConvertOptions


def assets_dir() -> Path:
    """Папка со встроенными ресурсами (устойчиво к сборке PyInstaller)."""
    if getattr(sys, "frozen", False):  # запущено из .exe
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        candidate = base / "markforge" / "assets"
        if candidate.exists():
            return candidate
        return base / "assets"
    return Path(__file__).resolve().parent.parent / "assets"


def presets_dir() -> Path:
    return assets_dir() / "presets"


@dataclass(frozen=True)
class Preset:
    name: str
    title: str
    reference_doc: Optional[str] = None  # имя файла в presets_dir()
    css: Optional[str] = None  # имя файла в presets_dir()


# Встроенные пресеты. Файлы подхватываются, только если реально существуют.
PRESETS: Dict[str, Preset] = {
    "default": Preset("default", "Стандартный", None, None),
    "clean": Preset("clean", "Чистый (Word)", reference_doc="reference-clean.docx"),
    "book": Preset("book", "Книга (EPUB/HTML)", css="book.css"),
    "article": Preset("article", "Статья (HTML/PDF)", css="article.css"),
}


def list_presets() -> Dict[str, str]:
    """Имя пресета -> человекочитаемое название."""
    return {name: p.title for name, p in PRESETS.items()}


def apply_preset(options: ConvertOptions) -> None:
    """Раскрыть ``options.preset`` в ``reference_doc``/``css`` (если файлы есть).

    Изменяет ``options`` на месте. Явно заданные пользователем пути не трогает.
    """
    name = options.preset
    if not name:
        return
    preset = PRESETS.get(name)
    if preset is None:
        return  # неизвестный пресет — молча игнорируем, чтобы не ломать конвертацию

    base = presets_dir()
    if preset.reference_doc and options.reference_doc is None:
        path = base / preset.reference_doc
        if path.exists():
            options.reference_doc = path
    if preset.css and options.css is None:
        path = base / preset.css
        if path.exists():
            options.css = path
