"""HTTP-сервис MarkForge на FastAPI — мост для мобильного/веб-приложения.

Без состояния: каждый запрос = загрузка файла → конвертация во временной папке
→ отдача результата (файл или .zip). Временные файлы удаляются после ответа.
Будущее приложение (React Native / Flutter / веб) вызывает эти же эндпоинты,
переиспользуя ядро 1:1 — логика конвертации не дублируется.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from starlette.background import BackgroundTask

from markforge import __version__
from markforge.core.engine import convert
from markforge.core.errors import (
    BackendUnavailableError,
    ConversionFailedError,
    CorruptInputError,
    MarkForgeError,
    UnknownFormatError,
    UnsupportedConversionError,
)
from markforge.core.formats import Format
from markforge.core.options import ConvertOptions
from markforge.core.registry import REGISTRY

app = FastAPI(title="MarkForge API", version=__version__)


@app.get("/health")
def health() -> dict:
    from markforge.core.backends.pandoc_locate import pandoc_available
    from markforge.core.backends.pdf import find_pdf_engine

    return {
        "status": "ok",
        "version": __version__,
        "pandoc": pandoc_available(),
        "pdf_engine": find_pdf_engine(),
    }


@app.get("/formats")
def formats() -> dict:
    pairs = []
    for (s, d), _names in REGISTRY.all_pairs().items():
        avail = [b.name for b in REGISTRY.available_backends_for(s, d)]
        pairs.append({"from": s.value, "to": d.value, "backends": avail})
    return {
        "formats": [f.value for f in Format],
        "targets": [f.value for f in Format if f != Format.PDF] + ["pdf"],
        "pairs": pairs,
    }


@app.post("/convert")
async def convert_endpoint(
    file: UploadFile = File(...),
    target_format: str = Form(...),
    source_format: Optional[str] = Form(None),
    backend: str = Form("auto"),
    options_json: Optional[str] = Form(None),
) -> FileResponse:
    tmp = Path(tempfile.mkdtemp(prefix="markforge_api_"))
    try:
        # Санитизация имени: только базовое имя, без компонентов пути (защита от traversal).
        safe_name = Path((file.filename or "input").replace("\\", "/")).name
        if not safe_name or safe_name in (".", ".."):
            safe_name = "input"
        in_path = tmp / safe_name
        with in_path.open("wb") as fh:
            shutil.copyfileobj(file.file, fh)

        opts = ConvertOptions()
        if options_json:
            try:
                opts = ConvertOptions(**json.loads(options_json))
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(422, f"Некорректный options_json: {exc}")
        opts.zip_output = True  # результат с медиа отдаём одним .zip

        out_dir = tmp / "out"
        out_dir.mkdir()
        result = convert(
            in_path,
            target_format,
            source_format=source_format,
            options=opts,
            backend=backend if backend in ("auto", "pandoc", "native") else "auto",
            output=out_dir,
        )
        artifact = result.artifact
        media = "application/zip" if artifact.suffix == ".zip" else _media_type(result.target_format)
        headers = {}
        if result.warnings:
            # percent-encode: HTTP-заголовки допускают только latin-1, а warnings — с кириллицей
            headers["X-MarkForge-Warnings"] = quote(" | ".join(result.warnings)[:900])
        headers["X-MarkForge-Backend"] = result.backend_used
        return FileResponse(
            path=str(artifact),
            media_type=media,
            filename=artifact.name,
            headers=headers,
            background=BackgroundTask(shutil.rmtree, tmp, ignore_errors=True),
        )
    except (UnknownFormatError, UnsupportedConversionError) as e:
        shutil.rmtree(tmp, ignore_errors=True)
        raise HTTPException(422, str(e))
    except BackendUnavailableError as e:
        shutil.rmtree(tmp, ignore_errors=True)
        raise HTTPException(503, str(e))
    except (CorruptInputError, ConversionFailedError, MarkForgeError) as e:
        shutil.rmtree(tmp, ignore_errors=True)
        raise HTTPException(400, str(e))
    except HTTPException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    except Exception as e:  # noqa: BLE001
        shutil.rmtree(tmp, ignore_errors=True)
        raise HTTPException(500, f"Внутренняя ошибка: {e}")


_MEDIA_TYPES = {
    "markdown": "text/markdown; charset=utf-8",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "epub": "application/epub+zip",
    "html": "text/html; charset=utf-8",
    "pdf": "application/pdf",
}


def _media_type(fmt: str) -> str:
    return _MEDIA_TYPES.get(fmt, "application/octet-stream")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    """Мини-страница для ручной проверки API (не основной интерфейс)."""
    targets = "".join(
        f"<option value='{f.value}'>{f.title}</option>"
        for f in Format
    )
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<title>MarkForge API</title><style>
body{{font-family:Segoe UI,system-ui,sans-serif;max-width:640px;margin:40px auto;padding:0 16px;color:#1a1a1a}}
h1{{color:#2d6cdf}} .card{{border:1px solid #e3e5e8;border-radius:12px;padding:20px}}
label{{display:block;margin:10px 0 4px;font-weight:600}} select,input,button{{font-size:15px;padding:8px}}
button{{background:#2d6cdf;color:#fff;border:0;border-radius:8px;padding:10px 18px;margin-top:16px;cursor:pointer}}
small{{color:#8a8f98}}</style></head><body>
<h1>MarkForge API</h1>
<p>Мост конвертации для мобильного/веб-приложения. Версия {__version__}.</p>
<div class="card"><form action="/convert" method="post" enctype="multipart/form-data">
<label>Файл</label><input type="file" name="file" required>
<label>Конвертировать в</label><select name="target_format">{targets}</select>
<label>Движок</label><select name="backend">
<option value="auto">auto</option><option value="pandoc">pandoc</option><option value="native">native</option></select>
<button type="submit">Конвертировать</button></form></div>
<p><small>API: <code>GET /formats</code>, <code>GET /health</code>, <code>POST /convert</code>.
Документация: <a href="/docs">/docs</a></small></p>
</body></html>"""


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run()
