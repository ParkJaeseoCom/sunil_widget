"""출결 위젯: 나이스 16기호 기록 — 완전 로컬(외부 전송 없음), 번호만 저장.

순수부(기호표·기록 헬퍼·파서·Excel 빌더)는 Task 2~4, GUI는 Task 5.
"""

from __future__ import annotations

import calendar
import datetime
import re

from openpyxl import Workbook
from openpyxl.styles import PatternFill

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


_DATE_RE = re.compile(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일|(\d{1,2})[/.](\d{1,2})")
_NUMBER_RE = re.compile(r"^(\d{1,3})\s*번")
_CLEAR_WORDS = {"취소", "지움", "지우기"}

_PREFIX_TO_REASON = {"질병": "질병", "미인정": "미인정", "기타": "기타", "인정": "출석인정"}


def _build_keyword_map() -> dict:
    table = {"체험학습": ("결석", "출석인정")}
    for status in STATUSES:
        table[status] = (status, "질병")  # 기본 사유
        for prefix, reason in _PREFIX_TO_REASON.items():
            table[prefix + status] = (status, reason)
    return table


_KEYWORDS = _build_keyword_map()


def parse_command(text: str, today: datetime.date,
                  ref_year: int | None = None) -> dict | None:
    """자연어 출결 명령 파싱(결정적 — AI 아님). 실패 시 None."""
    text = text.strip()
    m_num = _NUMBER_RE.match(text)
    if not m_num:
        return None
    number = int(m_num.group(1))
    rest = text[m_num.end():].strip()

    date_iso = None
    m_date = _DATE_RE.search(rest)
    if m_date:
        month = int(m_date.group(1) or m_date.group(3))
        day = int(m_date.group(2) or m_date.group(4))
        year = ref_year or today.year
        try:
            date_iso = datetime.date(year, month, day).isoformat()
        except ValueError:
            return None
        rest = (rest[: m_date.start()] + rest[m_date.end():]).strip()

    word = rest.replace(" ", "")
    if not word:
        return None
    if word in _CLEAR_WORDS:
        return {"number": number, "date": date_iso, "clear": True}
    if word in _KEYWORDS:
        status, reason = _KEYWORDS[word]
        return {"number": number, "date": date_iso,
                "status": status, "reason": reason}
    return None


_WEEKEND_FILL = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")


def months_with_records(data: dict) -> list[str]:
    return sorted({d[:7] for d in data.get("records", {})})


def _legend_text() -> str:
    parts = []
    for status in STATUSES:
        cells = " ".join(f"{reason}{SYMBOLS[(status, reason)]}" for reason in REASONS)
        parts.append(f"{status}: {cells}")
    return "  |  ".join(parts)


def build_attendance_workbook(data: dict, numbers: list[int],
                              months: list[str]) -> Workbook:
    wb = Workbook()
    wb.remove(wb.active)  # 기본 시트 제거
    for ym in months:
        year, month = int(ym[:4]), int(ym[5:7])
        last_day = calendar.monthrange(year, month)[1]
        ws = wb.create_sheet(title=ym)
        ws.cell(row=1, column=1, value=f"{year}년 {month}월 출결")
        ws.cell(row=2, column=1, value=_legend_text())
        ws.cell(row=4, column=1, value="번호")
        for day in range(1, last_day + 1):
            cell = ws.cell(row=4, column=day + 1, value=day)
            if datetime.date(year, month, day).weekday() >= 5:
                cell.fill = _WEEKEND_FILL
        symbols = month_symbols(data, year, month)
        for row_idx, number in enumerate(numbers, start=5):
            ws.cell(row=row_idx, column=1, value=number)
            for day in range(1, last_day + 1):
                sym = symbols.get((number, day))
                if sym:
                    ws.cell(row=row_idx, column=day + 1, value=sym)
    return wb
