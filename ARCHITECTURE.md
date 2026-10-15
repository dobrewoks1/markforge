# Архитектура MarkForge

Главная идея — **разделение ядра и интерфейсов**. Логика конвертации не знает
ничего про GUI/CLI/HTTP. Благодаря этому её можно переиспользовать где угодно
(в т.ч. в будущем мобильном приложении) и легко расширять.

```
              ┌─────────── интерфейсы (surfaces) ───────────┐
   CLI  ──▶   │  cli.py     gui.py (Tkinter)     service/api │  ◀── HTTP (мобилка/веб)
              └───────────────────┬─────────────────────────┘
                                  │  convert(src, target, options, backend)
              ┌───────────────────▼─────────────────────────┐
              │                  ЯДРО (core)                 │
              │  engine → registry → backend → media/bundle  │
              └───────────────────┬─────────────────────────┘
                     ┌────────────┴────────────┐
              PandocBackend               NativeBackend
              (subprocess pandoc)      (python-docx/mammoth/
                                        ebooklib/markdown/xhtml2pdf)
```

## Слои ядра (`markforge/core`)

| Модуль | Ответственность |
|--------|-----------------|
| `formats.py` | `Format` (enum), определение формата по расширению, канонические расширения |
| `options.py` | `ConvertOptions` и `ConvertResult` (pydantic) — единый контракт настроек/результата |
| `errors.py` | иерархия исключений |
| `registry.py` | реестр пар `(источник, цель) → [backend'ы]`, точка расширения |
| `engine.py` | `convert()` — выбор backend, временная папка, финализация, очистка |
| `media.py` | форма результата: одиночный файл / папка `имя/` + `media/` / `.zip` |
| `presets.py` | пресеты оформления (имя → `reference.docx`/`css`) |
| `backends/` | `pandoc_backend`, `native_backend`, `pandoc_locate`, `pdf` |

## Поток одной конвертации

1. `engine.convert()` определяет форматы `src`/`dst`, применяет пресет к опциям.
2. `_select_backend()` берёт из реестра backend'ы для пары и выбирает первый
   доступный (`auto` = pandoc → native), либо форсированный (`pandoc`/`native`).
3. Создаётся временная рабочая папка. Backend пишет туда результат
   (`имя.ext` и, при извлечении картинок, `media/`).
4. `media.finalize_output()` раскладывает результат к цели:
   - нет медиа → одиночный файл;
   - есть медиа → папка `имя/` (`имя.ext` + `media/`) или `.zip` (опция `zip_output`).
5. Временная папка удаляется. Возвращается `ConvertResult`.

## Два режима работы pandoc (важно для картинок)

- **Встраивание** (цель = docx/epub/pdf или самодостаточный html): pandoc
  запускается с рабочей папкой = папка исходника; относительные картинки
  «вшиваются» в контейнер. Результат — один файл.
- **Извлечение** (цель = markdown или обычный html): pandoc запускается с
  рабочей папкой = папка результата, флагом `--extract-media=media` и
  относительным именем вывода. Картинки уходят в `media/`, ссылки переписываются
  относительно файла — результат самодостаточен и переносим.

Windows-детали: аргументы передаются списком (пробелы/юникод в путях безопасны),
кодировка ввода-вывода принудительно UTF-8, флаг `CREATE_NO_WINDOW` (нет мигающей
консоли из GUI/.exe), таймаут на процесс.

## Границы качества native-движка

| Пара | Реализация | Качество |
|------|------------|----------|
| md ↔ html | markdown / markdownify | отличное |
| docx → md | mammoth → markdownify (+media) | хорошее |
| epub → md | ebooklib → markdownify (+media) | хорошее |
| md → epub | markdown → ebooklib | хорошее |
| * → pdf | HTML → xhtml2pdf | среднее (кириллица ОК) |
| md → docx, html → docx | BeautifulSoup → python-docx | базовое |
| docx ↔ epub | — | оставлено pandoc |

Каждый backend объявляет поддерживаемые пары через `supports()`, поэтому
интерфейс всегда знает, что доступно, и может предупредить о «базовом» качестве.

## Как расширять

**Новый формат:**
1. Добавьте значение в `Format` и расширение в `_EXT_MAP`/`CANONICAL_EXT` (`formats.py`).
2. Реализуйте пары в нужном backend'е и зарегистрируйте их в
   `backends/__init__.py` (`REGISTRY.register_backend(...)`).
3. Всё. Существующий код трогать не нужно — движок диспетчеризует по реестру.

**Новый backend** (например, LibreOffice-headless или облачный сервис):
```python
class MyBackend:
    name = "mybackend"
    def is_available(self): ...
    def supports(self, src, dst): ...
    def convert(self, input_path, work_dir, out_name, src, dst, options): ...

REGISTRY.register_backend(MyBackend(), [(Format.DOCX, Format.PDF), ...])
```
Порядок регистрации задаёт приоритет при `backend="auto"`. Для сторонних плагинов
предусмотрена группа entry points `markforge.backends` в `pyproject.toml`.

**Новая опция:** добавьте поле в `ConvertOptions` — оно автоматически доступно
во всех интерфейсах. Люк `extra_pandoc_args` позволяет передать любой флаг pandoc
без правки кода.

**Новый пресет оформления:** положите `reference.docx`/`.css` в
`markforge/assets/presets/` и добавьте запись в `PRESETS` (`presets.py`).

## Тесты

`tests/test_conversions.py` — прогон обоих backend'ов на реальных файлах
(пары, требующие pandoc, пропускаются без него), проверка извлечения медиа,
round-trip и обработки ошибок. Запуск: `python -m pytest`.
