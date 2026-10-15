"""Простая локализация интерфейса (RU/EN)."""

from __future__ import annotations

from typing import Dict

STRINGS: Dict[str, Dict[str, str]] = {
    "ru": {
        "app_title": "MarkForge — конвертер документов",
        "files": "Файлы",
        "drop_hint": "Перетащите файлы сюда\nили нажмите «Добавить файлы»",
        "add_files": "Добавить файлы",
        "remove": "Убрать",
        "clear": "Очистить",
        "settings": "Настройки",
        "target_format": "Конвертировать в:",
        "backend": "Движок:",
        "backend_auto": "Авто (лучшее качество)",
        "backend_pandoc": "pandoc",
        "backend_native": "Встроенный (без pandoc)",
        "options": "Опции",
        "opt_toc": "Оглавление",
        "opt_zip": "Упаковать результат с картинками в ZIP",
        "opt_embed": "Самодостаточный HTML (картинки внутри)",
        "opt_number": "Нумеровать разделы",
        "opt_overwrite": "Перезаписывать файлы с тем же именем",
        "epub_meta": "Метаданные (для EPUB)",
        "meta_title": "Заголовок:",
        "meta_author": "Автор:",
        "meta_lang": "Язык:",
        "preset": "Пресет оформления:",
        "output": "Куда сохранять",
        "out_same": "Рядом с исходным файлом",
        "out_choose": "Выбрать папку…",
        "convert": "Конвертировать",
        "converting": "Конвертация…",
        "ready": "Готово к работе",
        "done_one": "Готово: {name}",
        "done_all": "Завершено: успешно {ok}, ошибок {fail}",
        "error": "Ошибка",
        "warn": "Предупреждение",
        "open_folder": "Открыть папку результата",
        "no_files": "Сначала добавьте файлы.",
        "same_format": "пропущен (уже в этом формате)",
        "lang_button": "EN",
        "log": "Журнал",
        "col_file": "Файл",
        "col_status": "Статус",
        "status_queued": "в очереди",
        "status_ok": "готово",
        "status_fail": "ошибка",
        "status_skip": "пропущен",
        "pandoc_missing": "pandoc не найден — доступен встроенный движок (базовое качество).",
        "menu_about": "О программе",
        "about_text": (
            "MarkForge {ver}\n\nУниверсальный конвертер документов:\n"
            "Markdown ↔ Word ↔ EPUB ↔ HTML ↔ PDF.\n\n"
            "Ядро переиспользуется в CLI, этом окне и HTTP-сервисе\n"
            "(мост для будущего мобильного приложения)."
        ),
    },
    "en": {
        "app_title": "MarkForge — document converter",
        "files": "Files",
        "drop_hint": "Drop files here\nor click “Add files”",
        "add_files": "Add files",
        "remove": "Remove",
        "clear": "Clear",
        "settings": "Settings",
        "target_format": "Convert to:",
        "backend": "Engine:",
        "backend_auto": "Auto (best quality)",
        "backend_pandoc": "pandoc",
        "backend_native": "Built-in (no pandoc)",
        "options": "Options",
        "opt_toc": "Table of contents",
        "opt_zip": "Pack result with images into ZIP",
        "opt_embed": "Self-contained HTML (images inline)",
        "opt_number": "Number sections",
        "opt_overwrite": "Overwrite files with the same name",
        "epub_meta": "Metadata (for EPUB)",
        "meta_title": "Title:",
        "meta_author": "Author:",
        "meta_lang": "Language:",
        "preset": "Style preset:",
        "output": "Output location",
        "out_same": "Next to the source file",
        "out_choose": "Choose folder…",
        "convert": "Convert",
        "converting": "Converting…",
        "ready": "Ready",
        "done_one": "Done: {name}",
        "done_all": "Finished: {ok} ok, {fail} failed",
        "error": "Error",
        "warn": "Warning",
        "open_folder": "Open output folder",
        "no_files": "Add files first.",
        "same_format": "skipped (already this format)",
        "lang_button": "RU",
        "log": "Log",
        "col_file": "File",
        "col_status": "Status",
        "status_queued": "queued",
        "status_ok": "done",
        "status_fail": "failed",
        "status_skip": "skipped",
        "pandoc_missing": "pandoc not found — built-in engine available (basic quality).",
        "menu_about": "About",
        "about_text": (
            "MarkForge {ver}\n\nUniversal document converter:\n"
            "Markdown ↔ Word ↔ EPUB ↔ HTML ↔ PDF.\n\n"
            "The core is reused by the CLI, this window and an HTTP service\n"
            "(a bridge for a future mobile app)."
        ),
    },
}


class I18n:
    def __init__(self, lang: str = "ru") -> None:
        self.lang = lang if lang in STRINGS else "ru"

    def t(self, key: str, **kwargs: object) -> str:
        text = STRINGS[self.lang].get(key) or STRINGS["ru"].get(key) or key
        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception:  # pragma: no cover
                return text
        return text

    def toggle(self) -> None:
        self.lang = "en" if self.lang == "ru" else "ru"
