"""Точка входа: ``python -m markforge``.

Без аргументов открывает оконное приложение (GUI). С аргументами работает как
CLI (``python -m markforge convert ...``, ``... serve``, ``... doctor`` и т.д.).
"""

from __future__ import annotations

from markforge.surfaces.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
