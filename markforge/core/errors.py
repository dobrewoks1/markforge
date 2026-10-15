"""Иерархия исключений MarkForge."""

from __future__ import annotations

from typing import Optional


class MarkForgeError(Exception):
    """Базовое исключение всех ошибок конвертации."""


class UnknownFormatError(MarkForgeError):
    """Не удалось определить формат (по расширению/имени)."""


class UnsupportedConversionError(MarkForgeError):
    """Нет ни одного backend для пары (источник, цель)."""


class BackendUnavailableError(MarkForgeError):
    """Нужный backend недоступен (например, pandoc не установлен)."""


class CorruptInputError(MarkForgeError):
    """Входной файл повреждён или не является заявленным форматом."""


class ConversionFailedError(MarkForgeError):
    """Backend завершился с ошибкой во время конвертации."""

    def __init__(
        self,
        message: str,
        *,
        returncode: Optional[int] = None,
        stderr: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr

    def __str__(self) -> str:  # pragma: no cover - косметика
        base = super().__str__()
        if self.stderr:
            tail = self.stderr.strip().splitlines()[-5:]
            return base + "\n" + "\n".join(tail)
        return base
