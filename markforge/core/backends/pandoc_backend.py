"""Backend на базе pandoc — первичный, максимальное качество.

Два режима по направлению конвертации (см. дизайн):

* **Встраивание медиа** (цель = docx/epub/pdf или самодостаточный html):
  запускаем pandoc с ``cwd`` = папка исходника, чтобы относительные картинки
  подхватились и «вшились» в контейнер. Результат — одиночный файл.
* **Извлечение медиа** (цель = markdown или обычный html):
  запускаем pandoc с ``cwd`` = рабочая папка, ``--extract-media=media`` и
  относительным именем вывода. Картинки уезжают в ``media/`` рядом с файлом,
  ссылки переписываются относительно него — результат самодостаточен.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from markforge.core.backends.base import BackendOutput
from markforge.core.backends.pandoc_locate import find_pandoc, pandoc_available
from markforge.core.backends.pdf import find_pdf_engine
from markforge.core.errors import ConversionFailedError
from markforge.core.formats import Format
from markforge.core.options import ConvertOptions

_CREATE_NO_WINDOW = 0x08000000  # не мигать консолью из GUI/.exe

# Format -> имя читателя pandoc.
_READERS = {
    Format.MARKDOWN: "markdown+task_lists",
    Format.DOCX: "docx",
    Format.EPUB: "epub",
    Format.HTML: "html",
}

# Format -> имя писателя pandoc (markdown резолвится через _writer_name из flavor).
_WRITERS = {
    Format.DOCX: "docx",
    Format.EPUB: "epub3",
    Format.HTML: "html5",
}
_TARGETS = {Format.MARKDOWN, Format.DOCX, Format.EPUB, Format.HTML}


def _writer_name(dst: Format, o: ConvertOptions) -> str:
    if dst == Format.MARKDOWN:
        return o.markdown_flavor
    return _WRITERS[dst]


class PandocBackend:
    name = "pandoc"

    def is_available(self) -> bool:
        return pandoc_available()

    def supports(self, src: Format, dst: Format) -> bool:
        if not self.is_available():
            return False
        if dst == Format.PDF:
            return find_pdf_engine() is not None
        return src in _READERS and dst in _TARGETS

    # ------------------------------------------------------------------ #
    def convert(
        self,
        input_path: Path,
        work_dir: Path,
        out_name: str,
        src: Format,
        dst: Format,
        options: ConvertOptions,
    ) -> BackendOutput:
        input_path = Path(input_path).resolve()
        bundle = _produces_media_bundle(dst, options)

        if bundle:
            cwd = work_dir
            in_arg = str(input_path)
            out_arg = out_name
        else:
            cwd = input_path.parent
            in_arg = input_path.name
            out_arg = str((work_dir / out_name).resolve())

        args = self._build_args(in_arg, out_arg, src, dst, options, bundle, input_path)
        proc = _run_pandoc(args, cwd)
        warnings = _parse_warnings(proc.stderr)
        return BackendOutput(warnings=warnings, log=proc.stderr or "")

    # ------------------------------------------------------------------ #
    def _build_args(
        self,
        in_arg: str,
        out_arg: str,
        src: Format,
        dst: Format,
        o: ConvertOptions,
        bundle: bool,
        input_path: Path,
    ) -> List[str]:
        args: List[str] = ["-f", _READERS[src]]

        if dst == Format.PDF:
            engine = o.pdf_engine or find_pdf_engine()
            args += ["-o", out_arg]
            if engine:
                args += [f"--pdf-engine={engine}"]
            if o.toc:
                args += ["--toc", f"--toc-depth={o.toc_depth}"]
            if o.css:
                args += [f"--css={o.css}"]
            args += _resource_path_args(o, input_path)
            args += [in_arg]
            args += o.extra_pandoc_args
            return args

        args += ["-t", _writer_name(dst, o)]

        # Целостный документ нужен для docx/epub/самодостаточного html.
        if dst in (Format.DOCX, Format.EPUB) or (dst == Format.HTML and o.standalone):
            args += ["--standalone"]

        if dst == Format.MARKDOWN:
            args += [f"--wrap={o.wrap}"]
            if o.atx_headings:
                args += ["--markdown-headings=atx"]

        if bundle and o.extract_media:
            args += [f"--extract-media={o.media_dir_name}"]

        if o.toc and dst != Format.MARKDOWN:
            args += ["--toc", f"--toc-depth={o.toc_depth}"]
        if o.number_sections:
            args += ["--number-sections"]

        if dst == Format.DOCX and o.reference_doc:
            args += [f"--reference-doc={o.reference_doc}"]

        if dst in (Format.HTML, Format.EPUB) and o.css:
            args += [f"--css={o.css}"]

        if dst == Format.HTML and o.embed_resources:
            args += ["--embed-resources", "--standalone"]

        if dst == Format.EPUB:
            args += _epub_metadata_args(o)

        if dst == Format.HTML and o.standalone:
            args += ["--metadata", "title=Документ"]

        args += _resource_path_args(o, input_path)
        args += ["-o", out_arg, in_arg]
        args += o.extra_pandoc_args
        return args


def _produces_media_bundle(dst: Format, o: ConvertOptions) -> bool:
    if dst == Format.MARKDOWN:
        return True
    if dst == Format.HTML and not o.embed_resources:
        return True
    return False


def _epub_metadata_args(o: ConvertOptions) -> List[str]:
    m = o.epub
    args: List[str] = []
    if m.title:
        args += ["--metadata", f"title={m.title}"]
    for author in m.authors:
        args += ["--metadata", f"author={author}"]
    args += ["--metadata", f"lang={m.language or 'ru'}"]
    if m.date:
        args += ["--metadata", f"date={m.date}"]
    if m.publisher:
        args += ["--metadata", f"publisher={m.publisher}"]
    if m.identifier:
        args += ["--metadata", f"identifier={m.identifier}"]
    if m.cover_image:
        args += [f"--epub-cover-image={Path(m.cover_image).resolve()}"]
    return args


def _resource_path_args(o: ConvertOptions, input_path: Path) -> List[str]:
    args: List[str] = []
    # Папка исходника — чтобы относительные картинки находились всегда.
    args += [f"--resource-path={input_path.parent}"]
    for p in o.resource_path:
        args += [f"--resource-path={Path(p).resolve()}"]
    return args


def _run_pandoc(args: List[str], cwd: Path) -> subprocess.CompletedProcess:
    exe = find_pandoc()
    if not exe:
        raise ConversionFailedError("pandoc не найден в системе.")
    flags = _CREATE_NO_WINDOW if sys.platform == "win32" else 0
    try:
        proc = subprocess.run(
            [exe, *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=flags,
            timeout=600,
        )
    except subprocess.TimeoutExpired as exc:  # pragma: no cover
        raise ConversionFailedError("pandoc: превышено время конвертации (600с).") from exc
    if proc.returncode != 0:
        raise ConversionFailedError(
            "pandoc завершился с ошибкой.",
            returncode=proc.returncode,
            stderr=proc.stderr,
        )
    return proc


def _parse_warnings(stderr: Optional[str]) -> List[str]:
    if not stderr:
        return []
    out: List[str] = []
    for line in stderr.splitlines():
        line = line.strip()
        if not line:
            continue
        if "WARNING" in line or "warning" in line:
            out.append(line)
    return out
