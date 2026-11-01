"""Редактирование секретов перед записью в логи и журнал.

SPEC §17: пароли, токены и полные секреты авторизации не попадают в обычные
логи. Фильтр применяется и к сообщениям логгера, и к строкам audit_log.
"""

from __future__ import annotations

import logging
import re
from typing import Any

_SECRET_KEYS = re.compile(
    r"(?i)\b(token|secret|password|passwd|api[_\-]?key|authorization|cookie|session)\b"
    r"\s*[:=]\s*([\"']?)([^\s\"',;]{4,})\2"
)
_BEARER = re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9\-._~+/=]{8,}")
_LONG_TOKEN = re.compile(r"\b(sk|pk|ghp|xox[baprs])[-_][A-Za-z0-9\-_]{12,}\b")


def redact(text: str) -> str:
    text = _SECRET_KEYS.sub(lambda m: f"{m.group(1)}=***", text)
    text = _BEARER.sub(lambda m: f"{m.group(1)} ***", text)
    text = _LONG_TOKEN.sub("***", text)
    return text


def redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, dict):
        return {
            key: ("***" if _SECRET_KEYS.match(str(key)) else redact_value(item))
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact_value(item) for item in value]
    return value


class RedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact(record.msg)
        if record.args:
            record.args = tuple(
                redact(arg) if isinstance(arg, str) else arg for arg in record.args
            )
        return True
