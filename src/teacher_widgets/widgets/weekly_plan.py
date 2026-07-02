"""주간학습계획 위젯: 순수 함수부 (Task 2). Worker·Widget은 Task 3."""

from __future__ import annotations

import datetime

PLAN_TIERS = [(0, "compact"), (300, "two_days"), (480, "week")]

_SPECIAL_DEPT = "학사일정"


def week_monday(today: datetime.date) -> datetime.date:
    """표시 기준 월요일. 주말이면 다음 주 월요일."""
    if today.weekday() >= 5:
        return today + datetime.timedelta(days=7 - today.weekday())
    return today - datetime.timedelta(days=today.weekday())


def build_schedules_query(start_iso: str, end_iso: str) -> dict:
    def _f(op: str, value: str) -> dict:
        return {"fieldFilter": {"field": {"fieldPath": "date"}, "op": op,
                                "value": {"stringValue": value}}}

    return {
        "from": [{"collectionId": "schedules"}],
        "where": {"compositeFilter": {"op": "AND", "filters": [
            _f("GREATER_THAN_OR_EQUAL", start_iso),
            _f("LESS_THAN_OR_EQUAL", end_iso),
        ]}},
        "orderBy": [{"field": {"fieldPath": "date"}, "direction": "ASCENDING"}],
        "limit": 200,
    }


def _sv(fields: dict, key: str) -> str:
    return fields.get(key, {}).get("stringValue", "")


def parse_schedule_docs(docs: list[dict]) -> list[dict]:
    out = []
    for d in docs:
        f = d.get("fields", {})
        order_raw = f.get("order", {}).get("integerValue")
        out.append({
            "date": _sv(f, "date"),
            "department": _sv(f, "department"),
            "content": _sv(f, "content"),
            "order": int(order_raw) if order_raw is not None else 0,
        })
    return out


def parse_messages_doc(fs_doc: dict | None) -> dict:
    fields = (fs_doc or {}).get("fields", {})
    return {
        "principal": _sv(fields, "principal"),
        "vicePrincipal": _sv(fields, "vicePrincipal"),
    }


def group_entries(entries: list) -> dict:
    grouped: dict = {}
    for e in entries:
        grouped.setdefault(e["date"], []).append(e)
    for items in grouped.values():
        items.sort(key=lambda e: (0 if e["department"] == _SPECIAL_DEPT else 1,
                                  e.get("order", 0)))
    return grouped


def pick_days(tier: str, base_monday: datetime.date,
              today: datetime.date) -> list[datetime.date]:
    base = today if base_monday <= today <= base_monday + datetime.timedelta(days=4) \
        else base_monday
    if tier == "compact":
        return [base]
    if tier == "two_days":
        return [base, base + datetime.timedelta(days=1)]
    days = [base_monday + datetime.timedelta(days=i) for i in range(5)]
    days.append(base_monday + datetime.timedelta(days=7))
    return days
