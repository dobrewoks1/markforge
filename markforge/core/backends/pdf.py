"""PDF: определение движка pandoc и запасной путь HTML→PDF (xhtml2pdf).

Кириллица: встроенные шрифты PDF (Helvetica/Times) её не поддерживают. Поэтому
мы регистрируем системные TTF-шрифты напрямую в reportlab и сообщаем их имена
xhtml2pdf через его карту шрифтов (``DEFAULT_FONT``). Это надёжнее ``@font-face``,
который на Windows упирается в заблокированный временный файл шрифта.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import List, Optional, Tuple

from markforge.core.errors import ConversionFailedError

# Движки PDF для pandoc в порядке предпочтения.
_PANDOC_PDF_ENGINES = [
    "xelatex",
    "lualatex",
    "tectonic",
    "pdflatex",
    "wkhtmltopdf",
    "weasyprint",
    "prince",
    "context",
]


def find_pdf_engine() -> Optional[str]:
    """Найти установленный PDF-движок для pandoc (или None)."""
    for engine in _PANDOC_PDF_ENGINES:
        if shutil.which(engine):
            return engine
    return None


_WIN_FONTS = Path(r"C:\Windows\Fonts")

# (regular, bold, italic, bold-italic) — семейства с кириллицей.
_SANS_FAMILIES: List[Tuple[str, str, str, str]] = [
    ("arial.ttf", "arialbd.ttf", "ariali.ttf", "arialbi.ttf"),
    ("segoeui.ttf", "segoeuib.ttf", "segoeuii.ttf", "segoeuiz.ttf"),
    ("calibri.ttf", "calibrib.ttf", "calibrii.ttf", "calibriz.ttf"),
    ("tahoma.ttf", "tahomabd.ttf", "tahoma.ttf", "tahomabd.ttf"),
    ("verdana.ttf", "verdanab.ttf", "verdanai.ttf", "verdanaz.ttf"),
    ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans-Oblique.ttf",
     "DejaVuSans-BoldOblique.ttf"),
]
_MONO_FAMILIES: List[Tuple[str, str, str, str]] = [
    ("consola.ttf", "consolab.ttf", "consolai.ttf", "consolaz.ttf"),
    ("cour.ttf", "courbd.ttf", "couri.ttf", "courbi.ttf"),
    ("DejaVuSansMono.ttf", "DejaVuSansMono-Bold.ttf", "DejaVuSansMono-Oblique.ttf",
     "DejaVuSansMono-BoldOblique.ttf"),
]

SANS_NAME = "DocFont"
MONO_NAME = "DocMono"

_fonts_state: Optional[bool] = None  # None=не пробовали, True/False=результат


def _register_family(name: str, quartet: Tuple[str, str, str, str]) -> bool:
    """Зарегистрировать TTF-семейство в reportlab и в карте xhtml2pdf."""
    from reportlab.lib.fonts import addMapping
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from xhtml2pdf import default as x_default

    regular, bold, italic, bold_italic = quartet
    reg_path = _WIN_FONTS / regular
    if not reg_path.exists():
        return False

    def pick(fname: str) -> Path:
        p = _WIN_FONTS / fname
        return p if p.exists() else reg_path

    try:
        pdfmetrics.registerFont(TTFont(name, str(reg_path)))
        pdfmetrics.registerFont(TTFont(f"{name}-Bold", str(pick(bold))))
        pdfmetrics.registerFont(TTFont(f"{name}-Italic", str(pick(italic))))
        pdfmetrics.registerFont(TTFont(f"{name}-BoldItalic", str(pick(bold_italic))))
    except Exception:  # noqa: BLE001 — шрифт не подошёл, пробуем следующий
        return False

    addMapping(name, 0, 0, name)
    addMapping(name, 1, 0, f"{name}-Bold")
    addMapping(name, 0, 1, f"{name}-Italic")
    addMapping(name, 1, 1, f"{name}-BoldItalic")
    # Сообщаем xhtml2pdf имя шрифта (ключи в нижнем регистре, значение — как в reportlab).
    x_default.DEFAULT_FONT[name.lower()] = name
    return True


def ensure_fonts() -> bool:
    """Зарегистрировать шрифты с кириллицей (один раз). True, если удалось."""
    global _fonts_state
    if _fonts_state is not None:
        return _fonts_state
    try:
        sans_ok = any(_register_family(SANS_NAME, q) for q in _SANS_FAMILIES)
        for q in _MONO_FAMILIES:
            if _register_family(MONO_NAME, q):
                break
    except Exception:  # noqa: BLE001
        sans_ok = False
    _fonts_state = bool(sans_ok)
    return _fonts_state


_BASE_CSS = """
body { font-family: 'DocFont', Helvetica, sans-serif; font-size: 11pt;
       line-height: 1.45; color: #1a1a1a; }
h1, h2, h3, h4, h5, h6 { font-family: 'DocFont', sans-serif; color: #111;
       margin: 1.1em 0 0.4em; line-height: 1.2; }
h1 { font-size: 22pt; } h2 { font-size: 17pt; } h3 { font-size: 14pt; }
p { margin: 0 0 0.6em; }
code, pre { font-family: 'DocMono', 'Courier New', monospace; font-size: 9.5pt; }
pre { background: #f4f4f4; border: 1px solid #e0e0e0; padding: 8px; }
code { background: #f4f4f4; padding: 1px 3px; }
blockquote { color: #555; border-left: 3px solid #ccc; margin: 0.6em 0;
             padding-left: 12px; }
table { border-collapse: collapse; width: 100%; margin: 0.6em 0; }
th, td { border: 1px solid #bbb; padding: 5px 8px; text-align: left; }
th { background: #f0f0f0; }
img { max-width: 100%; }
a { color: #1155cc; text-decoration: none; }
"""


def _page_css(page_size: str) -> str:
    return f"@page {{ size: {page_size}; margin: 2cm; }}"


def _build_html(body: str, title: str, page_size: str, user_css: Optional[str]) -> str:
    css_parts = [_page_css(page_size), _BASE_CSS]
    if user_css:
        css_parts.append(user_css)
    style = "\n".join(css_parts)
    safe_title = title or "Документ"
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>{safe_title}</title><style>{style}</style></head>"
        f"<body>{body}</body></html>"
    )


def _link_callback(base_dir: Path):
    def resolve(uri: str, rel: str) -> str:
        if uri.startswith(("data:", "http://", "https://", "file:")):
            return uri
        candidate = Path(uri)
        if candidate.is_absolute() and candidate.exists():
            return str(candidate)
        return str((base_dir / uri).resolve())

    return resolve


def render_html_to_pdf(
    body: str,
    out_path: Path,
    *,
    base_dir: Path,
    title: str = "",
    page_size: str = "A4",
    user_css: Optional[str] = None,
) -> List[str]:
    """Отрендерить HTML-фрагмент ``body`` в PDF ``out_path``. Требует xhtml2pdf."""
    try:
        from xhtml2pdf import pisa
    except ImportError as exc:  # pragma: no cover
        raise ConversionFailedError(
            "Для экспорта в PDF нужен пакет xhtml2pdf (pip install xhtml2pdf) "
            "или PDF-движок (wkhtmltopdf/LaTeX) для pandoc."
        ) from exc

    fonts_ok = ensure_fonts()
    html = _build_html(body, title, page_size, user_css)
    warnings: List[str] = []
    if not fonts_ok:
        warnings.append(
            "Не найден системный TTF-шрифт — кириллица в PDF может отображаться неверно."
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with out_path.open("wb") as fh:
            status = pisa.CreatePDF(
                src=html,
                dest=fh,
                encoding="utf-8",
                link_callback=_link_callback(base_dir),
            )
    except Exception as exc:  # noqa: BLE001 — напр. CSSParseError из-за кривого CSS
        out_path.unlink(missing_ok=True)
        raise ConversionFailedError(
            f"Не удалось сгенерировать PDF (возможно, некорректный CSS): {exc}"
        ) from exc
    if status.err:
        out_path.unlink(missing_ok=True)
        raise ConversionFailedError(f"xhtml2pdf: ошибок при генерации PDF: {status.err}")
    return warnings
