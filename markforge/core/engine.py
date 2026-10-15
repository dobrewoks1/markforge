"""Оркестрация конвертации: выбор backend, временная папка, финализация.

Публичная точка входа — :func:`convert`.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Optional, Union

from markforge.core.errors import (
    BackendUnavailableError,
    CorruptInputError,
    UnsupportedConversionError,
)
from markforge.core.formats import (
    OUTPUT_ONLY,
    Format,
    coerce_format,
    detect_format,
)
from markforge.core.media import default_dest_file, finalize_output
from markforge.core.options import BackendChoice, ConvertOptions, ConvertResult
from markforge.core.registry import REGISTRY

# Триггерим саморегистрацию backend'ов в REGISTRY.
import markforge.core.backends  # noqa: E402,F401
from markforge.core.presets import apply_preset  # noqa: E402


def convert(
    source: Union[str, Path],
    target_format: Union[Format, str],
    *,
    source_format: Union[Format, str, None] = None,
    options: Optional[ConvertOptions] = None,
    backend: BackendChoice = "auto",
    output: Union[str, Path, None] = None,
) -> ConvertResult:
    """Сконвертировать ``source`` в ``target_format``.

    :param source: путь к исходному файлу.
    :param target_format: формат-цель (``Format`` или строка вроде ``"docx"``).
    :param source_format: явный формат источника (по умолчанию — по расширению).
    :param options: параметры конвертации (:class:`ConvertOptions`).
    :param backend: ``"auto"`` (pandoc, иначе native), ``"pandoc"`` или ``"native"``.
    :param output: путь результата (файл или папка); None = рядом с источником.
    :returns: :class:`ConvertResult`.
    """
    src_path = Path(source)
    if not src_path.exists():
        raise FileNotFoundError(f"Файл не найден: {src_path}")
    if not src_path.is_file():
        raise CorruptInputError(f"Это не файл: {src_path}")

    src = coerce_format(source_format) if source_format else detect_format(src_path)
    dst = coerce_format(target_format)

    if src in OUTPUT_ONLY:
        raise UnsupportedConversionError(
            f"Из формата {src.title} конвертация не поддерживается (только как цель)."
        )
    if src == dst:
        raise UnsupportedConversionError(
            f"Источник и цель совпадают ({src.title}) — конвертировать нечего."
        )

    opts = (options or ConvertOptions()).model_copy(deep=True)
    apply_preset(opts)

    chosen = _select_backend(src, dst, backend)

    dest_file = default_dest_file(src_path.resolve(), dst, output)

    work_dir = Path(tempfile.mkdtemp(prefix="markforge_"))
    try:
        out_name = dest_file.name
        backend_out = chosen.convert(
            input_path=src_path.resolve(),
            work_dir=work_dir,
            out_name=out_name,
            src=src,
            dst=dst,
            options=opts,
        )
        return finalize_output(
            work_dir=work_dir,
            out_name=out_name,
            dest_file=dest_file,
            src_format=src,
            dst_format=dst,
            source_path=src_path.resolve(),
            backend_used=chosen.name,
            options=opts,
            warnings=backend_out.warnings,
            log=backend_out.log,
        )
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def _select_backend(src: Format, dst: Format, choice: BackendChoice):
    candidates = REGISTRY.backends_for(src, dst)
    if not candidates:
        raise UnsupportedConversionError(
            f"Нет конвертера для {src.title} → {dst.title}."
        )

    if choice != "auto":
        for b in candidates:
            if b.name == choice:
                if b.is_available() and b.supports(src, dst):
                    return b
                raise BackendUnavailableError(
                    f"Backend '{choice}' недоступен для {src.title} → {dst.title}."
                )
        raise UnsupportedConversionError(
            f"Backend '{choice}' не умеет {src.title} → {dst.title}."
        )

    for b in candidates:
        if b.is_available() and b.supports(src, dst):
            return b

    raise BackendUnavailableError(
        f"Нет доступного backend для {src.title} → {dst.title}. "
        "Установите pandoc для максимального качества."
    )
