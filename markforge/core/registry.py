"""Реестр конвертеров: пара (источник, цель) -> список backend'ов.

Это точка расширяемости. Новый backend или формат добавляется вызовом
``REGISTRY.register_backend(...)`` без изменения существующего кода.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Tuple

from markforge.core.formats import Format

if TYPE_CHECKING:  # избегаем циклического импорта: backends импортируют реестр
    from markforge.core.backends.base import Backend

Pair = Tuple[Format, Format]


@dataclass
class ConverterRegistry:
    # (src, dst) -> имена backend'ов в порядке предпочтения
    _pairs: Dict[Pair, List[str]] = field(default_factory=dict)
    _backends: Dict[str, Backend] = field(default_factory=dict)

    def register_backend(self, backend: Backend, pairs: List[Pair]) -> None:
        self._backends[backend.name] = backend
        for pair in pairs:
            names = self._pairs.setdefault(pair, [])
            if backend.name not in names:
                names.append(backend.name)

    def backend(self, name: str) -> Backend:
        return self._backends[name]

    def backends_for(self, src: Format, dst: Format) -> List[Backend]:
        """Все backend'ы, заявляющие пару (в порядке предпочтения)."""
        return [self._backends[n] for n in self._pairs.get((src, dst), [])]

    def available_backends_for(self, src: Format, dst: Format) -> List[Backend]:
        """Только реально доступные и подтверждающие поддержку пары."""
        return [
            b
            for b in self.backends_for(src, dst)
            if b.is_available() and b.supports(src, dst)
        ]

    def all_pairs(self) -> Dict[Pair, List[str]]:
        return dict(self._pairs)

    def supported_targets(self, src: Format) -> List[Format]:
        """Форматы-цели, в которые можно перевести данный источник (сейчас)."""
        targets: List[Format] = []
        for (s, d) in self._pairs:
            if s == src and d not in targets and self.available_backends_for(s, d):
                targets.append(d)
        return targets


# Глобальный реестр. Backend'ы регистрируются при импорте markforge.core.backends.
REGISTRY = ConverterRegistry()
