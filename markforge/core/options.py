"""Модели настроек конвертации и результата (pydantic v2).

Единый ``ConvertOptions`` протекает без изменений через CLI, GUI и HTTP-сервис
и попадает в backend. Это делает добавление опций дешёвым и согласованным.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

MarkdownFlavor = Literal["gfm", "commonmark_x", "markdown"]
WrapMode = Literal["none", "auto", "preserve"]
BackendChoice = Literal["auto", "pandoc", "native"]


class EpubMetadata(BaseModel):
    """Метаданные для сборки EPUB."""

    title: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    language: str = "ru"
    date: Optional[str] = None
    publisher: Optional[str] = None
    identifier: Optional[str] = None  # ISBN / UUID
    cover_image: Optional[Path] = None


class ConvertOptions(BaseModel):
    """Все параметры конвертации в одном месте."""

    # --- вид Markdown на выходе ---
    markdown_flavor: MarkdownFlavor = "gfm"
    wrap: WrapMode = "none"
    atx_headings: bool = True

    # --- структура документа ---
    toc: bool = False
    toc_depth: int = 3
    number_sections: bool = False

    # --- медиа/картинки ---
    extract_media: bool = True
    media_dir_name: str = "media"
    zip_output: bool = False  # упаковать результат-папку в .zip

    # --- перезапись ---
    # False (по умолчанию) — не трогаем существующие файлы/папки: результат
    # получает уникальное имя «имя (1)». True — перезаписываем на месте.
    overwrite: bool = False

    # --- HTML ---
    embed_resources: bool = False  # самодостаточный html (картинки как data-URI)
    standalone: bool = True

    # --- оформление ---
    reference_doc: Optional[Path] = None  # шаблон стилей для Word (.docx)
    css: Optional[Path] = None  # css для HTML/EPUB/PDF
    preset: Optional[str] = None  # имя пресета (резолвится в reference_doc/css)

    # --- EPUB ---
    epub: EpubMetadata = Field(default_factory=EpubMetadata)

    # --- PDF ---
    pdf_engine: Optional[str] = None  # None = авто (pandoc-движок или xhtml2pdf)
    pdf_page_size: str = "A4"

    # --- поиск ресурсов (картинки для md/html -> docx/epub/pdf) ---
    resource_path: List[Path] = Field(default_factory=list)

    # --- запасной люк: добавляется в конец списка аргументов pandoc ---
    extra_pandoc_args: List[str] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}


class ConvertResult(BaseModel):
    """Результат конвертации."""

    source_path: Path
    output_path: Path  # основной артефакт (.md/.docx/.epub/.html/.pdf)
    source_format: str
    target_format: str
    backend_used: str  # "pandoc" | "native"
    is_bundle: bool = False  # результат = папка (md + media)
    media_dir: Optional[Path] = None
    bundle_path: Optional[Path] = None  # .zip, если создавался
    warnings: List[str] = Field(default_factory=list)
    log: str = ""

    model_config = {"arbitrary_types_allowed": True}

    @property
    def artifact(self) -> Path:
        """Файл, который логично отдать пользователю (zip, если он есть)."""
        return self.bundle_path or self.output_path
