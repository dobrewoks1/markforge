"""Контракт backend'а конвертации.

Каждый backend пишет результат в ``work_dir`` под именем ``out_name`` и,
при необходимости, извлекает медиа в ``work_dir/<media_dir_name>/``. Финальное
размещение (одиночный файл / папка / zip) выполняет движок (``engine.py``),
поэтому все backends дают одинаковую по форме выдачу.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Protocol, Tuple, runtime_checkable

from markforge.core.formats import Format
from markforge.core.options import ConvertOptions


@dataclass
class BackendOutput:
    """Что backend сообщает движку после конвертации."""

    warnings: List[str] = field(default_factory=list)
    log: str = ""


@runtime_checkable
class Backend(Protocol):
    """Интерфейс backend'а. Реализуйте его и зарегистрируйте в REGISTRY."""

    name: str

    def is_available(self) -> bool:
        """Доступен ли backend в текущем окружении."""
        ...

    def supports(self, src: Format, dst: Format) -> bool:
        """Поддерживает ли backend конкретную пару прямо сейчас."""
        ...

    def convert(
        self,
        input_path: Path,
        work_dir: Path,
        out_name: str,
        src: Format,
        dst: Format,
        options: ConvertOptions,
    ) -> BackendOutput:
        """Сконвертировать ``input_path`` в ``work_dir/out_name``."""
        ...


Pair = Tuple[Format, Format]
