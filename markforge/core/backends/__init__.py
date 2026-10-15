"""Backends конвертации и их саморегистрация в реестре.

Импорт этого пакета регистрирует все доступные backends. Порядок регистрации
для каждой пары = порядок предпочтения при ``backend="auto"`` (pandoc первым).
"""

from __future__ import annotations

from markforge.core.formats import Format as F
from markforge.core.registry import REGISTRY
from markforge.core.backends.pandoc_backend import PandocBackend
from markforge.core.backends.native_backend import NativeBackend

# --- pandoc умеет любые пары между текстовыми/контейнерными форматами ---
_PANDOC_PAIRS = [
    (F.MARKDOWN, F.DOCX),
    (F.DOCX, F.MARKDOWN),
    (F.MARKDOWN, F.EPUB),
    (F.EPUB, F.MARKDOWN),
    (F.MARKDOWN, F.HTML),
    (F.HTML, F.MARKDOWN),
    (F.DOCX, F.EPUB),
    (F.EPUB, F.DOCX),
    (F.DOCX, F.HTML),
    (F.HTML, F.DOCX),
    (F.EPUB, F.HTML),
    (F.HTML, F.EPUB),
    # PDF пандоком — только если в системе есть pdf-движок (проверяется в supports()).
    (F.MARKDOWN, F.PDF),
    (F.HTML, F.PDF),
    (F.DOCX, F.PDF),
    (F.EPUB, F.PDF),
]

# --- native backend покрывает реалистичное подмножество (см. native_backend) ---
_NATIVE_PAIRS = [
    (F.MARKDOWN, F.HTML),
    (F.HTML, F.MARKDOWN),
    (F.DOCX, F.MARKDOWN),
    (F.EPUB, F.MARKDOWN),
    (F.MARKDOWN, F.EPUB),
    (F.MARKDOWN, F.DOCX),  # базовая точность
    (F.HTML, F.DOCX),  # базовая точность
    # PDF через xhtml2pdf (чистый Python) — работает всегда.
    (F.MARKDOWN, F.PDF),
    (F.HTML, F.PDF),
    (F.DOCX, F.PDF),
    (F.EPUB, F.PDF),
]

REGISTRY.register_backend(PandocBackend(), _PANDOC_PAIRS)
REGISTRY.register_backend(NativeBackend(), _NATIVE_PAIRS)

__all__ = ["PandocBackend", "NativeBackend"]
