# -*- coding: utf-8 -*-
"""Тесты ядра конвертации MarkForge (pytest).

Прогоняются обе backend'а на реальных файлах. Пары, требующие pandoc,
пропускаются, если pandoc не установлен.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from markforge import ConvertOptions, Format, convert
from markforge.core.backends.pandoc_locate import pandoc_available
from markforge.core.errors import UnsupportedConversionError
from markforge.core.formats import CANONICAL_EXT
from markforge.core.registry import REGISTRY

HAS_PANDOC = pandoc_available()

SAMPLE_MD = """---
title: Тест
author: Автор
lang: ru
---

# Заголовок

Абзац с **жирным**, *курсивом* и `кодом`. Кириллица.

- один
- два

| A | B |
|---|---|
| 1 | 2 |

![картинка](logo.png)

> цитата
"""


@pytest.fixture()
def sample(tmp_path: Path) -> Path:
    from PIL import Image

    Image.new("RGB", (80, 40), (40, 100, 180)).save(tmp_path / "logo.png")
    md = tmp_path / "sample.md"
    md.write_text(SAMPLE_MD, encoding="utf-8")
    return md


def _backends_for(src: Format, dst: Format):
    names = [b.name for b in REGISTRY.available_backends_for(src, dst)]
    return names


# --- параметризация по парам и backend'ам ---
PAIRS = [
    (Format.MARKDOWN, Format.DOCX),
    (Format.MARKDOWN, Format.EPUB),
    (Format.MARKDOWN, Format.HTML),
    (Format.MARKDOWN, Format.PDF),
]


@pytest.mark.parametrize("dst", [Format.DOCX, Format.EPUB, Format.HTML, Format.PDF])
@pytest.mark.parametrize("backend", ["native", "pandoc"])
def test_from_markdown(sample: Path, tmp_path: Path, dst: Format, backend: str):
    if backend == "pandoc" and not HAS_PANDOC:
        pytest.skip("pandoc не установлен")
    if backend not in _backends_for(Format.MARKDOWN, dst):
        pytest.skip(f"{backend} не поддерживает MD→{dst.value}")
    out = tmp_path / f"out_{backend}{CANONICAL_EXT[dst]}"
    res = convert(sample, dst, backend=backend, output=out,
                  options=ConvertOptions(epub={"title": "Т", "authors": ["А"]}))
    assert res.artifact.exists()
    assert res.artifact.stat().st_size > 0
    assert res.backend_used == backend


@pytest.mark.skipif(not HAS_PANDOC, reason="pandoc нужен для docx→md")
def test_docx_to_md_extracts_media(sample: Path, tmp_path: Path):
    docx = tmp_path / "d.docx"
    convert(sample, Format.DOCX, backend="pandoc", output=docx)
    res = convert(docx, Format.MARKDOWN, backend="pandoc",
                  options=ConvertOptions(zip_output=True), output=tmp_path / "back.md")
    # результат с картинкой => zip-бандл
    assert res.is_bundle
    assert res.artifact.suffix == ".zip"
    with zipfile.ZipFile(res.artifact) as z:
        names = z.namelist()
    assert any(n.endswith(".md") for n in names)
    assert any("media/" in n for n in names)


def test_native_docx_to_md(sample: Path, tmp_path: Path):
    # docx делаем любым доступным backend'ом, читаем native'ом
    docx = tmp_path / "d.docx"
    convert(sample, Format.DOCX, output=docx)
    res = convert(docx, Format.MARKDOWN, backend="native", output=tmp_path / "b.md")
    text = res.output_path.read_text(encoding="utf-8")
    assert "Заголовок" in text


def test_roundtrip_md_html_md(sample: Path, tmp_path: Path):
    html = convert(sample, Format.HTML, backend="native", output=tmp_path / "a.html")
    back = convert(html.output_path, Format.MARKDOWN, backend="native", output=tmp_path / "b.md")
    text = back.output_path.read_text(encoding="utf-8")
    assert "Заголовок" in text
    assert "жирным" in text


def test_pdf_has_content(sample: Path, tmp_path: Path):
    res = convert(sample, Format.PDF, backend="native", output=tmp_path / "o.pdf")
    data = res.output_path.read_bytes()
    assert data[:4] == b"%PDF"
    assert len(data) > 1000


def test_same_format_rejected(sample: Path, tmp_path: Path):
    with pytest.raises(UnsupportedConversionError):
        convert(sample, Format.MARKDOWN, output=tmp_path / "x.md")


def test_pdf_is_output_only(tmp_path: Path):
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    with pytest.raises(UnsupportedConversionError):
        convert(pdf, Format.MARKDOWN, output=tmp_path / "x.md")


def test_registry_has_expected_pairs():
    pairs = REGISTRY.all_pairs()
    assert (Format.MARKDOWN, Format.DOCX) in pairs
    assert (Format.DOCX, Format.MARKDOWN) in pairs
    assert (Format.MARKDOWN, Format.PDF) in pairs
    # native всегда доступен
    assert "native" in [b.name for b in REGISTRY.available_backends_for(
        Format.MARKDOWN, Format.HTML)]
