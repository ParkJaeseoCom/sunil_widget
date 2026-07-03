"""출결 위젯: 나이스 16기호 기록 — 완전 로컬(외부 전송 없음), 번호만 저장.

순수부(기호표·기록 헬퍼·파서·Excel 빌더)는 Task 2~4, GUI는 Task 5.
"""

from __future__ import annotations

STATUSES = ["결석", "지각", "조퇴", "결과"]
REASONS = ["질병", "미인정", "기타", "출석인정"]

_SYMBOL_ROWS = {
    "결석": ["♡", "♥", "▲", "△"],
    "지각": ["#", "X", "≠", "◁"],
    "조퇴": ["@", "◎", "∽", "▷"],
    "결과": ["☆", "◇", "=", "▽"],
}
SYMBOLS = {
    (status, REASONS[i]): sym
    for status, row in _SYMBOL_ROWS.items()
    for i, sym in enumerate(row)
}


def symbol_for(status: str, reason: str) -> str:
    return SYMBOLS[(status, reason)]


def set_record(data: dict, date_iso: str, number: int, status: str, reason: str) -> None:
    records = data.setdefault("records", {})
    records.setdefault(date_iso, {})[str(number)] = {
        "status": status, "reason": reason,
    }


def clear_record(data: dict, date_iso: str, number: int) -> None:
    day = data.get("records", {}).get(date_iso)
    if not day:
        return
    day.pop(str(number), None)
    if not day:
        data["records"].pop(date_iso, None)


def get_record(data: dict, date_iso: str, number: int) -> dict | None:
    return data.get("records", {}).get(date_iso, {}).get(str(number))


def month_symbols(data: dict, year: int, month: int) -> dict:
    """해당 월의 {(번호, 일): 기호} 매핑."""
    prefix = f"{year:04d}-{month:02d}-"
    out: dict = {}
    for date_iso, day_records in data.get("records", {}).items():
        if not date_iso.startswith(prefix):
            continue
        day = int(date_iso[8:10])
        for num_str, rec in day_records.items():
            sym = SYMBOLS.get((rec.get("status"), rec.get("reason")))
            if sym:
                out[(int(num_str), day)] = sym
    return out
