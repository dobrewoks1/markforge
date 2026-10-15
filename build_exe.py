"""Сборка standalone .exe через PyInstaller.

Запуск:
    python build_exe.py                 # GUI-приложение (одиночный .exe, без консоли)
    python build_exe.py --bundle-pandoc # + вшить pandoc.exe внутрь (портативно, ~+150 МБ)
    python build_exe.py --console       # с консолью (для отладки)
    python build_exe.py --cli           # отдельный консольный markforge-cli.exe

Результат — в папке ``dist/``. Для сборки нужен PyInstaller:
    pip install pyinstaller
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SEP = ";" if os.name == "nt" else ":"


def _find_pandoc() -> str | None:
    import shutil

    p = shutil.which("pandoc")
    if p:
        return p
    local = os.environ.get("LOCALAPPDATA", "")
    cand = Path(local) / "Pandoc" / "pandoc.exe"
    return str(cand) if cand.exists() else None


def build(args: argparse.Namespace) -> int:
    try:
        import PyInstaller.__main__  # noqa: F401
    except ImportError:
        print("PyInstaller не установлен. Выполните: pip install pyinstaller", file=sys.stderr)
        return 1

    name = "markforge-cli" if args.cli else "MarkForge"
    entry = "markforge/surfaces/cli.py" if args.cli else "markforge/surfaces/gui.py"

    opts = [
        entry,
        "--name", name,
        "--onefile",
        "--noconfirm",
        "--clean",
        "--collect-all", "tkinterdnd2",
        "--collect-all", "xhtml2pdf",
        "--collect-all", "reportlab",
        "--collect-submodules", "ebooklib",
        "--collect-submodules", "markdown",
        "--collect-submodules", "markforge",
        "--hidden-import", "markdown_it",
        "--hidden-import", "PIL",
        "--add-data", f"{ROOT / 'markforge' / 'assets'}{SEP}markforge/assets",
    ]

    # GUI без консоли (для CLI консоль нужна).
    if args.cli or args.console:
        opts.append("--console")
    else:
        opts.append("--windowed")

    # Иконка, если есть.
    icon = ROOT / "markforge" / "assets" / "icon.ico"
    if icon.exists():
        opts += ["--icon", str(icon)]

    # Вшить pandoc.
    if args.bundle_pandoc:
        pandoc = _find_pandoc()
        if pandoc:
            opts += ["--add-binary", f"{pandoc}{SEP}pandoc"]
            print(f"Вшиваю pandoc: {pandoc}")
        else:
            print("pandoc не найден — собираю без него (будет использован системный/native).")

    print("PyInstaller аргументы:\n  " + " ".join(opts))
    import PyInstaller.__main__ as pim

    pim.run(opts)
    print(f"\nГотово. Файл: {ROOT / 'dist' / (name + '.exe')}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Сборка .exe MarkForge (PyInstaller)")
    parser.add_argument("--bundle-pandoc", action="store_true", help="вшить pandoc.exe")
    parser.add_argument("--console", action="store_true", help="оставить консоль (отладка)")
    parser.add_argument("--cli", action="store_true", help="собрать консольный markforge-cli.exe")
    return build(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
