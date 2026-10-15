# MarkForge — путь к мобильному приложению

Ядро конвертации уже отделено от интерфейса, поэтому мобильное приложение не
нужно писать «с нуля»: оно переиспользует ту же логику. Есть два пути — начните
с первого (быстрый результат), при необходимости перейдите ко второму.

## Путь A (рекомендуется для старта): тонкий клиент + HTTP-сервис

Мобильное приложение — это UI, который отправляет файл на сервис MarkForge и
получает результат. Сервис уже готов: `markforge/service/api.py` (FastAPI).

```
[Мобильное приложение]  ──(multipart/form-data)──▶  [MarkForge API]  ──▶  ядро
   React Native / Flutter        POST /convert          FastAPI          convert()
        UI, выбор файла      ◀──(файл .docx/.epub/.zip)──
```

### Контракт API

| Метод | Назначение |
|-------|------------|
| `GET /health` | статус, версия, наличие pandoc/pdf-движка |
| `GET /formats` | список поддерживаемых пар и доступных движков (для построения UI-выбора) |
| `POST /convert` | `file` + `target_format` (+ `source_format`, `backend`, `options_json`) → файл результата |

Результат отдаётся как файл; если есть картинки (например, `docx → md`) — как `.zip`.
Предупреждения приходят в заголовке `X-MarkForge-Warnings`, использованный движок —
в `X-MarkForge-Backend`.

### Пример запроса (любой язык)

```bash
curl -X POST http://SERVER:8000/convert \
  -F "file=@book.md" -F "target_format=epub" \
  -F 'options_json={"toc":true,"epub":{"title":"Книга","authors":["Автор"]}}' \
  -o book.epub
```

### Пример клиента (Flutter / Dart)

```dart
final req = http.MultipartRequest('POST', Uri.parse('$server/convert'))
  ..fields['target_format'] = 'epub'
  ..files.add(await http.MultipartFile.fromPath('file', path));
final res = await req.send();
final bytes = await res.stream.toBytes();      // сохранить/поделиться
```

### Пример клиента (React Native)

```js
const form = new FormData();
form.append('file', { uri, name: 'book.md', type: 'text/markdown' });
form.append('target_format', 'pdf');
const res = await fetch(`${server}/convert`, { method: 'POST', body: form });
const blob = await res.blob();                 // сохранить в файловую систему
```

### Где запускать сервис

- **Локально на ПК пользователя** — приложение в одной сети обращается к ПК.
- **В облаке** (любой хостинг с Docker/Python) — тогда нужен и pandoc в образе.
  Сервис без состояния (stateless), масштабируется горизонтально, временные
  файлы чистятся после ответа.

Минимальный Dockerfile для облака:

```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y pandoc && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . .
RUN pip install -e ".[service]"
EXPOSE 8000
CMD ["python", "-m", "markforge", "serve", "--host", "0.0.0.0", "--port", "8000"]
```

## Путь B (полностью офлайн): портирование ядра на устройство

Когда нужна работа без сети. Ядро (`markforge/core`) — обычный Python без
привязки к ОС, кроме поиска pandoc. Варианты:

- **Android** — [Chaquopy](https://chaquo.com/chaquopy/) (Python внутри Android):
  подключить `markforge.core` и зависимости-«чистый Python». pandoc на устройстве
  обычно недоступен, поэтому работает встроенный `native`-движок (его для этого и
  сделали). PDF идёт через `xhtml2pdf` (тоже чистый Python).
- **iOS** — сложнее из-за ограничений на исполнение кода; практичнее Путь A.
- **Kotlin/Swift-переписывание** — при желании native-логику можно повторить на
  целевом языке; контракт (`convert(src, dst, options) → result`) и границы
  качества уже описаны в [ARCHITECTURE.md](ARCHITECTURE.md).

### Что важно для офлайн-режима

- Встроенный `native`-движок не требует внешних программ — идеален для мобилки.
- Зависимости native-движка — «чистый Python» (`python-docx`, `mammoth`,
  `markdownify`, `ebooklib`, `markdown`, `beautifulsoup4`, `xhtml2pdf`,
  `reportlab`, `Pillow`), что упрощает упаковку.
- Для PDF на устройстве нужен TTF-шрифт с кириллицей — на десктопе берётся из
  системы; на мобилке его стоит вшить в ассеты приложения.

## Рекомендация

1. Сейчас: поднять `markforge serve` (локально или в облаке) и сделать простой
   мобильный UI по Пути A — это переиспользует весь готовый движок.
2. Позже, если понадобится офлайн: встроить `markforge.core` через Chaquopy
   (Android) по Пути B, оставив тот же контракт.
