"""Командная строка MarkForge.

Примеры:
    markforge convert book.md -t epub --title "Моя книга" --author "Имя"
    markforge convert doc.docx -t md --zip
    markforge batch ./docs -t pdf -o ./out --recursive
    markforge formats
    markforge doctor
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from markforge import __version__
from markforge.core.engine import convert
from markforge.core.errors import MarkForgeError
from markforge.core.formats import (
    INPUT_EXTENSIONS,
    Format,
    coerce_format,
    detect_format,
)
from markforge.core.options import ConvertOptions, EpubMetadata
from markforge.core.registry import REGISTRY


def _reconfigure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover
            pass


def _build_options(args: argparse.Namespace) -> ConvertOptions:
    epub = EpubMetadata(
        title=getattr(args, "title", None),
        authors=[getattr(args, "author")] if getattr(args, "author", None) else [],
        language=getattr(args, "lang", None) or "ru",
        cover_image=Path(args.cover) if getattr(args, "cover", None) else None,
    )
    return ConvertOptions(
        markdown_flavor=getattr(args, "flavor", None) or "gfm",
        toc=getattr(args, "toc", False),
        number_sections=getattr(args, "number_sections", False),
        zip_output=getattr(args, "zip", False),
        embed_resources=getattr(args, "embed", False),
        overwrite=getattr(args, "overwrite", False),
        reference_doc=Path(args.reference_doc) if getattr(args, "reference_doc", None) else None,
        css=Path(args.css) if getattr(args, "css", None) else None,
        preset=getattr(args, "preset", None),
        pdf_page_size=getattr(args, "page_size", None) or "A4",
        epub=epub,
    )


def _print_result(res, quiet: bool = False) -> None:
    if quiet:
        print(res.artifact)
        return
    kind = "папка+media" if res.is_bundle and not res.bundle_path else (
        "zip" if res.bundle_path else "файл"
    )
    print(f"  ✓ {res.source_path.name} → {res.artifact.name}  "
          f"[{res.backend_used}, {kind}]")
    for w in res.warnings:
        print(f"    ⚠ {w}")


def cmd_convert(args: argparse.Namespace) -> int:
    options = _build_options(args)
    src = Path(args.input)
    if not src.exists():
        print(f"Файл не найден: {src}", file=sys.stderr)
        return 2
    try:
        res = convert(
            src,
            args.to,
            options=options,
            backend=args.backend,
            output=Path(args.output) if args.output else None,
        )
    except MarkForgeError as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        return 1
    _print_result(res, quiet=args.quiet)
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    options = _build_options(args)
    root = Path(args.input)
    if not root.is_dir():
        print(f"Не папка: {root}", file=sys.stderr)
        return 2

    target = coerce_format(args.to)
    pattern = "**/*" if args.recursive else "*"
    out_dir = Path(args.output) if args.output else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    files = [
        p for p in sorted(root.glob(pattern))
        if p.is_file() and p.suffix.lower() in INPUT_EXTENSIONS
    ]
    if not files:
        print("Подходящих файлов не найдено.")
        return 0

    ok = 0
    fail = 0
    print(f"Пакетная конвертация {len(files)} файл(ов) → {target.title}:")
    for f in files:
        try:
            if detect_format(f) == target:
                continue
        except MarkForgeError:
            continue
        try:
            res = convert(f, target, options=options, backend=args.backend, output=out_dir)
            _print_result(res, quiet=args.quiet)
            ok += 1
        except MarkForgeError as e:
            print(f"  ✗ {f.name}: {e}", file=sys.stderr)
            fail += 1
    print(f"Готово: успешно {ok}, ошибок {fail}.")
    return 0 if fail == 0 else 1


def cmd_formats(args: argparse.Namespace) -> int:
    print("Поддерживаемые конвертации (источник → цель: backend'ы):\n")
    for (s, d), names in sorted(
        REGISTRY.all_pairs().items(), key=lambda kv: (kv[0][0].value, kv[0][1].value)
    ):
        avail = [b.name for b in REGISTRY.available_backends_for(s, d)]
        mark = ", ".join(avail) if avail else "— недоступно"
        print(f"  {s.title:14} → {d.title:14}  [{mark}]")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    from markforge.core.backends.pandoc_locate import find_pandoc
    from markforge.core.backends.pdf import find_pdf_engine

    print(f"MarkForge {__version__}")
    print(f"Python: {sys.version.split()[0]}  ({sys.platform})")
    pandoc = find_pandoc()
    print(f"pandoc: {pandoc or 'НЕ найден (будет использован native backend)'}")
    engine = find_pdf_engine()
    print(f"PDF-движок pandoc: {engine or 'нет (PDF через встроенный xhtml2pdf)'}")
    try:
        import xhtml2pdf  # noqa: F401
        print("xhtml2pdf: доступен (экспорт в PDF работает)")
    except ImportError:
        print("xhtml2pdf: НЕ установлен (PDF недоступен без pandoc-движка)")
    print(f"Пар конвертации зарегистрировано: {len(REGISTRY.all_pairs())}")
    return 0


def cmd_gui(args: argparse.Namespace) -> int:
    from markforge.surfaces.gui import main as gui_main

    gui_main()
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from markforge.service.api import run as serve_run

    serve_run(host=args.host, port=args.port)
    return 0


def _add_common_convert_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("-t", "--to", required=True, help="формат-цель: md/docx/epub/html/pdf")
    p.add_argument("-o", "--output", help="файл или папка результата")
    p.add_argument("--backend", choices=["auto", "pandoc", "native"], default="auto")
    p.add_argument("--flavor", choices=["gfm", "commonmark_x", "markdown"], help="вид Markdown")
    p.add_argument("--toc", action="store_true", help="оглавление")
    p.add_argument("--number-sections", action="store_true", dest="number_sections")
    p.add_argument("--zip", action="store_true", help="упаковать результат с media в .zip")
    p.add_argument("--embed", action="store_true", help="самодостаточный HTML (data-URI)")
    p.add_argument("--overwrite", action="store_true",
                   help="перезаписывать существующие файлы (иначе имя «(1)»)")
    p.add_argument("--title", help="заголовок (EPUB)")
    p.add_argument("--author", help="автор (EPUB)")
    p.add_argument("--lang", help="язык (EPUB), по умолчанию ru")
    p.add_argument("--cover", help="обложка EPUB (картинка)")
    p.add_argument("--reference-doc", dest="reference_doc", help="шаблон стилей Word (.docx)")
    p.add_argument("--css", help="CSS для HTML/EPUB/PDF")
    p.add_argument("--preset", help="пресет оформления (см. 'markforge formats')")
    p.add_argument("--page-size", dest="page_size", help="размер страницы PDF (A4/Letter…)")
    p.add_argument("-q", "--quiet", action="store_true", help="меньше вывода")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="markforge",
        description="MarkForge — универсальный конвертер документов (MD ↔ Word ↔ EPUB ↔ HTML ↔ PDF).",
    )
    parser.add_argument("--version", action="version", version=f"MarkForge {__version__}")
    sub = parser.add_subparsers(dest="command")

    p_conv = sub.add_parser("convert", help="конвертировать один файл")
    p_conv.add_argument("input", help="исходный файл")
    _add_common_convert_args(p_conv)
    p_conv.set_defaults(func=cmd_convert)

    p_batch = sub.add_parser("batch", help="конвертировать все файлы в папке")
    p_batch.add_argument("input", help="папка с файлами")
    p_batch.add_argument("--recursive", action="store_true", help="включая подпапки")
    _add_common_convert_args(p_batch)
    p_batch.set_defaults(func=cmd_batch)

    p_fmt = sub.add_parser("formats", help="список поддерживаемых конвертаций")
    p_fmt.set_defaults(func=cmd_formats)

    p_doc = sub.add_parser("doctor", help="проверка окружения")
    p_doc.set_defaults(func=cmd_doctor)

    p_gui = sub.add_parser("gui", help="запустить оконное приложение")
    p_gui.set_defaults(func=cmd_gui)

    p_srv = sub.add_parser("serve", help="запустить HTTP-сервис (мост для мобильного приложения)")
    p_srv.add_argument("--host", default="127.0.0.1")
    p_srv.add_argument("--port", type=int, default=8000)
    p_srv.set_defaults(func=cmd_serve)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    _reconfigure_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        # Без подкоманды — запускаем GUI (удобно при двойном клике по .exe).
        return cmd_gui(args)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
