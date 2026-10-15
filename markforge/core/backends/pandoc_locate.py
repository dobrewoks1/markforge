"""Поиск исполняемого файла pandoc (для рантайма и для сборки .exe)."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import List, Optional


def _candidates() -> List[Path]:
    out: List[Path] = []

    # 1. Явное указание через переменную окружения.
    env = os.environ.get("MARKFORGE_PANDOC")
    if env:
        out.append(Path(env))

    # 2. Рядом с замороженным .exe (PyInstaller кладёт в _MEIPASS/pandoc/).
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        out.append(base / "pandoc" / "pandoc.exe")
        out.append(base / "pandoc")

    # 3. Стандартное расположение установки на Windows.
    local = os.environ.get("LOCALAPPDATA")
    if local:
        out.append(Path(local) / "Pandoc" / "pandoc.exe")
    out.append(Path(r"C:\Program Files\Pandoc\pandoc.exe"))

    return out


# Кэшируем ТОЛЬКО положительный результат (и перепроверяем его существование),
# чтобы установка pandoc уже после старта программы подхватывалась без перезапуска.
_cached_pandoc: Optional[str] = None


def _search_pandoc() -> Optional[str]:
    for cand in _candidates():
        if cand.exists() and cand.is_file():
            return str(cand)
    return shutil.which("pandoc")


def find_pandoc() -> Optional[str]:
    """Вернуть путь к pandoc или None, если он не найден."""
    global _cached_pandoc
    if _cached_pandoc and Path(_cached_pandoc).exists():
        return _cached_pandoc
    _cached_pandoc = _search_pandoc()
    return _cached_pandoc


def pandoc_available() -> bool:
    return find_pandoc() is not None
