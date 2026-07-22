"""Custom column types."""
from __future__ import annotations

from enum import Enum

from sqlalchemy import Enum as SAEnum


def EnumStr(enum_cls: type[Enum], **kwargs):
    """A non-native (VARCHAR-backed) enum column that stores each member's
    ``.value`` and hydrates back into the Python enum on load.

    Keeps columns human-readable in SQLite while guaranteeing that attribute
    access yields real enum instances (so ``obj.field.value`` always works).
    """
    return SAEnum(
        enum_cls,
        native_enum=False,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
        **kwargs,
    )
