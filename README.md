# MarkForge — универсальный конвертер документов

> **English summary.** MarkForge is a desktop document converter for Windows: Markdown ↔ Word (.docx) ↔ EPUB ↔ HTML, plus export to PDF.
> One conversion core is shared by three interfaces: a Tkinter GUI (drag-and-drop, batch mode, RU/EN), a CLI and a small FastAPI HTTP service.
> It uses pandoc when it is installed and falls back to a built-in pure-Python engine otherwise; images are extracted to `media/` or packed into a ZIP.
> PDF export needs no external tools (xhtml2pdf) and handles Cyrillic using Windows system fonts.
> Tests: pytest; CI runs on Ubuntu and Windows. Built together with Claude Code (an AI coding assistant).
> The rest of this README is in Russian.

Конвертирует **Markdown ↔ Word (.docx) ↔ EPUB ↔ HTML ↔ PDF** в обе стороны.
Готовая программа для ПК (Windows) с оконным интерфейсом, командной строкой и
HTTP-сервисом. Архитектура рассчитана на расширение форматов и последующее
создание мобильного приложения.

<p align="center"><img src="samples/logo.png" alt="MarkForge" width="240"></p>

![Окно MarkForge: четыре файла сконвертированы в PDF](docs/screenshot.png)

## Что умеет

- **Оконное приложение** (перетаскивание файлов, пакетная конвертация, прогресс,
  выбор формата и оформления, RU/EN).
- **Пакетная конвертация** — сразу много файлов или целые папки.
- **Два движка**: `pandoc` (максимальное качество, если установлен) и встроенный
  `native` на чистом Python (работает без pandoc). Программа сама выбирает лучший.
- **Картинки и медиа** сохраняются: при конвертации в Markdown/HTML они
  извлекаются в папку `media/` рядом с файлом (или упаковываются в `.zip`).
- **Экспорт в PDF** с поддержкой кириллицы (встроенный движок, без внешних программ).
- **Пресеты оформления** и свои шаблоны стилей Word (`reference.docx`) и CSS.
- **HTTP-сервис** (FastAPI) — тот же движок конвертации по сети; основа для
  будущего мобильного/веб-приложения (см. [MOBILE.md](MOBILE.md)).

## Матрица форматов

| Из \ В        | Markdown | Word | EPUB | HTML | PDF |
|---------------|:--------:|:----:|:----:|:----:|:---:|
| **Markdown**  |    —     |  ✓   |  ✓   |  ✓   |  ✓  |
| **Word**      |    ✓     |  —   |  ✓   |  ✓   |  ✓  |
| **EPUB**      |    ✓     |  ✓   |  —   |  ✓   |  ✓  |
| **HTML**      |    ✓     |  ✓   |  ✓   |  —   |  ✓  |
| **PDF**       |    —     |  —   |  —   |  —   |  —  |

PDF — только как результат (из PDF обратно не конвертируем). Полный список с
указанием доступных движков: `markforge formats`.

## Установка

Нужен **Python 3.10+**. Для максимального качества желателен (не обязателен)
[pandoc](https://pandoc.org/installing.html).

**Вариант 1 — из исходников (быстро):**

```bat
install.bat            :: установит зависимости
run_gui.bat            :: запустит оконное приложение
```

или вручную:

```bat
python -m pip install -r requirements.txt
python -m markforge gui
```

**Вариант 2 — как пакет:**

```bat
python -m pip install -e .
markforge-gui
```

**Вариант 3 — собрать .exe (не требует Python у конечного пользователя):**

```bat
python -m pip install pyinstaller
python build_exe.py                 :: dist\MarkForge.exe  (окно, без консоли)
python build_exe.py --bundle-pandoc :: вшить pandoc внутрь (портативно)
```

## Использование

### Оконное приложение

`run_gui.bat` (или `python -m markforge gui`). Перетащите файлы в окно, выберите
формат-цель и нажмите «Конвертировать». Настройки (оглавление, ZIP, метаданные
EPUB, пресет, папка результата) — на правой панели.

### Командная строка

```bat
:: один файл
markforge convert book.md -t epub --title "Моя книга" --author "Имя" --toc
markforge convert doc.docx -t md --zip
markforge convert page.html -t pdf

:: целая папка (в т.ч. рекурсивно)
markforge batch .\docs -t pdf -o .\out --recursive

:: справка и диагностика
markforge formats
markforge doctor
```

Через `run_cli.bat`: `run_cli.bat convert book.md -t epub`.

Полезные ключи: `--backend auto|pandoc|native`, `--flavor gfm|markdown`,
`--toc`, `--number-sections`, `--zip`, `--embed` (самодостаточный HTML),
`--overwrite`, `--reference-doc styles.docx`, `--css style.css`, `--preset book`.

> **Безопасность данных.** По умолчанию существующие файлы и папки не
> перезаписываются: результат получает уникальное имя вида `имя (1).docx`.
> Флаг `--overwrite` (в окне — галочка «Перезаписывать файлы с тем же именем»)
> включает перезапись на месте. Программа никогда не пишет поверх исходного файла.

### HTTP-сервис (мост для мобильного приложения)

```bat
run_api.bat            :: http://127.0.0.1:8000  (форма проверки и /docs)
```

Эндпоинты: `POST /convert` (файл + `target_format`), `GET /formats`, `GET /health`.
Подробнее — [MOBILE.md](MOBILE.md).

### Из Python

```python
from markforge import convert, Format, ConvertOptions

res = convert("book.md", Format.EPUB,
              options=ConvertOptions(toc=True, epub={"title": "Книга", "authors": ["Автор"]}))
print(res.output_path, res.backend_used, res.warnings)
```

## Качество конвертации

- **pandoc** (движок по умолчанию, если установлен) — эталонное качество для всех пар.
- **native** (встроенный) — работает без pandoc. Отлично: `md↔html`, `docx→md`,
  `epub→md`, `md→epub`, любое `→pdf`. Базово (упрощённо): `md→docx`, `html→docx` —
  заголовки, абзацы, жирный/курсив, списки, таблицы, картинки. Для сложного
  форматирования Word лучше поставить pandoc.
- **PDF** генерируется из HTML встроенным движком (`xhtml2pdf`) с системными
  шрифтами (кириллица поддерживается). Если установить движок для pandoc
  (LaTeX / wkhtmltopdf), качество PDF станет выше автоматически.

## Структура проекта

```
markforge/
  core/            ядро (форматы, опции, движок, реестр, медиа, пресеты)
    backends/      pandoc / native / pdf
  surfaces/        cli.py, gui.py, i18n.py  (интерфейсы)
  service/         api.py  (FastAPI — мост для мобилки)
  assets/presets/  reference-clean.docx, book.css, article.css
samples/           пример документа (sample.md) и картинка к нему
tests/             pytest
docs/              скриншот для README
.github/workflows/ CI: pytest на Ubuntu и Windows
build_exe.py       сборка .exe
run_*.bat          лаунчеры
```

Как это устроено и как добавить новый формат/движок — [ARCHITECTURE.md](ARCHITECTURE.md).
План мобильного приложения — [MOBILE.md](MOBILE.md).

## Диагностика

- `markforge doctor` — покажет, найден ли pandoc, есть ли PDF-движок, сколько пар доступно.
- «pandoc не найден» — программа продолжит работать на встроенном движке; для
  лучшего качества установите pandoc.
- Кириллица в PDF выглядит неверно — не найден системный TTF-шрифт; обычно на
  Windows берётся Arial/Segoe UI автоматически.

## Как сделано

- **Ядро отдельно от интерфейсов.** `markforge/core` ничего не знает про окно,
  CLI и HTTP: все три интерфейса вызывают одну функцию `convert()`
  (подробности — в [ARCHITECTURE.md](ARCHITECTURE.md)).
- **Реестр пар «формат → формат → движок».** Новый формат или движок
  добавляется регистрацией в реестре, остальной код не меняется.
- **Два движка с автовыбором:** pandoc, если он установлен, иначе встроенный
  `native` на чистом Python.
- **Тесты:** `python -m pytest` — конвертации проверяются на настоящих файлах во
  временной папке; случаи, где нужен pandoc, без него пропускаются.
  CI — GitHub Actions на Ubuntu и Windows.
- **Разработано в связке с Claude Code** (ИИ-ассистент для программирования):
  задачи ставил и результат проверял я, код, тесты и документация написаны
  вместе с ИИ.

## Лицензия

MIT — см. [LICENSE](LICENSE). © 2026 Fyodor Poplavskiy (Фёдор Поплавский).
