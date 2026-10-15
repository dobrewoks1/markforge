"""Финализация вывода: одиночный файл / папка-бандл (md + media) / zip.

Единое место, где решается форма результата — благодаря этому все backend'ы
пишут во временную папку одинаково, а движок раскладывает результат к цели.

Безопасность данных (важно):
* существующие файлы/папки НЕ удаляются молча. По умолчанию (``overwrite=False``)
  при коллизии имени результат получает суффикс «(1)», «(2)»…;
* с ``overwrite=True`` перезапись выполняется явно;
* результат никогда не пишется поверх исходного файла (иначе — ошибка).
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import List, Optional

from markforge.core.errors import MarkForgeError
from markforge.core.formats import Format
from markforge.core.options import ConvertOptions, ConvertResult


def _dir_has_files(path: Path) -> bool:
    return path.is_dir() and any(p.is_file() for p in path.rglob("*"))


def _unique_path(path: Path) -> Path:
    """Вернуть несуществующий путь, добавляя «(n)» при коллизии."""
    if not path.exists():
        return path
    stem, suffix, parent = path.stem, path.suffix, path.parent
    i = 1
    while True:
        candidate = parent / f"{stem} ({i}){suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def _unique_dir(path: Path) -> Path:
    if not path.exists():
        return path
    i = 1
    while True:
        candidate = path.parent / f"{path.name} ({i})"
        if not candidate.exists():
            return candidate
        i += 1


def _resolve_file_target(dest_file: Path, overwrite: bool, source: Path) -> Path:
    """Куда положить одиночный файл-результат (с защитой данных)."""
    if (dest_file.parent.resolve() / dest_file.name) == source:
        raise MarkForgeError(
            "Путь результата совпадает с исходным файлом — перезапись источника "
            f"запрещена: {dest_file}"
        )
    if dest_file.exists() and dest_file.is_dir():
        raise MarkForgeError(f"По пути результата уже существует папка: {dest_file}")
    if dest_file.exists() and not overwrite:
        return _unique_path(dest_file)
    return dest_file


def _move_onto_file(src: Path, dst: Path) -> None:
    """Переместить src -> dst (существующий ФАЙЛ dst заменяем)."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.is_file():
        dst.unlink()
    shutil.move(str(src), str(dst))


def finalize_output(
    *,
    work_dir: Path,
    out_name: str,
    dest_file: Path,
    src_format: Format,
    dst_format: Format,
    source_path: Path,
    backend_used: str,
    options: ConvertOptions,
    warnings: List[str],
    log: str,
) -> ConvertResult:
    """Разложить результат из ``work_dir`` в конечное место ``dest_file``."""
    produced = work_dir / out_name
    if not produced.exists():
        candidates = [p for p in work_dir.iterdir() if p.suffix == dest_file.suffix]
        if candidates:
            produced = candidates[0]
        else:
            raise FileNotFoundError(f"Backend не создал ожидаемый файл: {produced}")

    source_resolved = source_path.resolve()
    media_dir = work_dir / options.media_dir_name
    has_media = _dir_has_files(media_dir)

    if not has_media:
        target = _resolve_file_target(dest_file, options.overwrite, source_resolved)
        _move_onto_file(produced, target)
        return ConvertResult(
            source_path=source_path,
            output_path=target,
            source_format=src_format.value,
            target_format=dst_format.value,
            backend_used=backend_used,
            is_bundle=False,
            media_dir=None,
            bundle_path=None,
            warnings=warnings,
            log=log,
        )

    # --- бандл: папка <stem>/ с основным файлом и media/ ---
    stem = dest_file.stem
    desired_dir = dest_file.parent / stem
    if (desired_dir.resolve() / dest_file.name) == source_resolved:
        raise MarkForgeError("Путь результата совпадает с исходным файлом.")
    bundle_dir = _unique_dir(desired_dir) if not options.overwrite else desired_dir

    if bundle_dir.exists() and options.overwrite:
        if bundle_dir.is_dir():
            shutil.rmtree(bundle_dir)
        else:
            bundle_dir.unlink()
    bundle_dir.mkdir(parents=True, exist_ok=True)

    main_in_bundle = bundle_dir / dest_file.name
    shutil.move(str(produced), str(main_in_bundle))
    shutil.move(str(media_dir), str(bundle_dir / options.media_dir_name))

    if options.zip_output:
        zip_target = _resolve_file_target(
            dest_file.with_suffix(".zip"), options.overwrite, source_resolved
        )
        base = zip_target.with_suffix("")
        made = Path(shutil.make_archive(str(base), "zip", root_dir=str(bundle_dir)))
        shutil.rmtree(bundle_dir, ignore_errors=True)
        return ConvertResult(
            source_path=source_path,
            output_path=made,
            source_format=src_format.value,
            target_format=dst_format.value,
            backend_used=backend_used,
            is_bundle=True,
            media_dir=None,
            bundle_path=made,
            warnings=warnings,
            log=log,
        )

    return ConvertResult(
        source_path=source_path,
        output_path=main_in_bundle,
        source_format=src_format.value,
        target_format=dst_format.value,
        backend_used=backend_used,
        is_bundle=True,
        media_dir=bundle_dir / options.media_dir_name,
        bundle_path=None,
        warnings=warnings,
        log=log,
    )


def default_dest_file(
    source_path: Path,
    dst_format: Format,
    output: Optional[Path],
) -> Path:
    """Вычислить конечный путь основного файла результата.

    ``output`` может быть None (рядом с источником), папкой или полным путём файла.
    """
    from markforge.core.formats import canonical_ext

    ext = canonical_ext(dst_format)
    if output is None:
        return source_path.with_name(source_path.stem + ext)

    output = Path(output)
    if output.is_dir() or output.suffix == "":
        return output / (source_path.stem + ext)
    return output
