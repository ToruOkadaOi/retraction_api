"""Shared notice classification; a database match is not necessarily a retraction."""

from collections import Counter
from collections.abc import Iterable

from sqlalchemy import func

from app.models import Retraction

_NOTICE_NAMES = {
    "retraction": "Retraction",
    "correction": "Correction",
    "expression of concern": "Expression of concern",
    "reinstatement": "Reinstatement",
}


def notice_type(value: str) -> str:
    return _NOTICE_NAMES.get(value.strip().lower(), value.strip() or "Unknown")


def count_notice_types(values: Iterable[str]) -> dict[str, int]:
    return dict(sorted(Counter(notice_type(value) for value in values).items()))


def is_retraction(value: str) -> bool:
    return notice_type(value) == "Retraction"


def retraction_filter():
    return func.lower(func.trim(Retraction.retraction_nature)) == "retraction"
