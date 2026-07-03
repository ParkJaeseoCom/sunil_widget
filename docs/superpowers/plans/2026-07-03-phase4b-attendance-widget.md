# Phase 4-B 출결 위젯 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 나이스 16기호로 학급 출결을 기록하는 완전 로컬 위젯 — 월별 그리드, 셀 퀵메뉴, 자연어 입력, openpyxl Excel 출력.

**Architecture:** 민감 로컬 파일 I/O(.bak 백업·손상 복구)는 `core/data_local.py`로 분리한다. 기호표·기록 헬퍼·자연어 파서·Excel 빌더는 순수 함수로 만들어 픽스처로 테스트한다. GUI는 QTableWidget 기반 월 그리드 + BaseWidget 상속(로컬형 — RemoteWidget 아님).

**Tech Stack:** Python 3.14, PySide6, **openpyxl(신규 의존성 — 순수 파이썬, PyInstaller 호환)**, pytest + pytest-qt.

## Global Constraints

- 데이터는 `store.path.parent / "attendance.json"` (config.json과 분리). **외부 전송 절대 금지**(네트워크 코드 접근 금지). 이름 저장 금지 — 번호만.
- 파일 구조: `{"records": {"YYYY-MM-DD": {"7": {"status": "결석", "reason": "질병"}}}}` (번호 키는 문자열).
- 기호표(정확히): 결석 질병♡ 미인정♥ 기타▲ 출석인정△ / 지각 질병# 미인정X 기타≠ 출석인정◁ / 조퇴 질병@ 미인정◎ 기타∽ 출석인정▷ / 결과 질병☆ 미인정◇ 기타= 출석인정▽. 체험학습=결석/출석인정.
- STATUSES = ["결석","지각","조퇴","결과"], REASONS = ["질병","미인정","기타","출석인정"].
- 저장 시 기존 파일 → `.bak` 복사. 손상 로드 시 `.bak` 복구, 그것도 실패 시 손상본을 `attendance.corrupt-<ts>.json`으로 보존 후 빈 데이터.
- 번호는 공유 `class_roster` (`ConfigStore.get_roster()` + `roster_numbers`).
- 자연어 문법·키워드 매핑은 spec §4 그대로 (기본 사유 질병, 체험학습→출석인정, 접두 질병/미인정/기타/인정, 취소어 취소/지움/지우기, 날짜 "N월 M일"|"N/M"|"N.M").
- 위젯 식별자 `attendance`. 테스트: offscreen, 네트워크 없음. 실행 `.venv/Scripts/python.exe -m pytest -v` (경로 따옴표).
- 커밋 footer: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. 기존 143 테스트 유지.

---

## 파일 구조

```
src/teacher_widgets/core/data_local.py    # (신규) load_json_with_backup / save_json_with_backup
src/teacher_widgets/widgets/attendance.py # (신규) 기호표·기록 헬퍼·파서·Excel 빌더 + AttendanceWidget
src/teacher_widgets/main.py               # (수정) attendance 등록
tests/test_data_local.py                  # (신규)
tests/test_attendance.py                  # (신규)
requirements.txt                          # (수정) openpyxl 추가
```

---

## Task 1: openpyxl 설치 + data_local (백업 파일 I/O)

**Files:**
- Create: `src/teacher_widgets/core/data_local.py`
- Modify: `requirements.txt`
- Test: `tests/test_data_local.py`

**Interfaces:**
- Consumes: (없음)
- Produces:
  - `load_json_with_backup(path: Path) -> dict` — 없으면 `{}`. 손상 시 `.bak` 시도 → 성공하면 그 내용, 실패하면 손상본을 `<stem>.corrupt-<YYYYmmddHHMMSS><suffix>`로 rename 후 `{}`.
  - `save_json_with_backup(path: Path, data: dict) -> None` — 기존 파일 있으면 `<path>.bak`으로 복사 후 UTF-8(ensure_ascii=False, indent=2) 저장. 부모 폴더 자동 생성.

- [ ] **Step 1: openpyxl 설치**

```bash
.venv/Scripts/python.exe -m pip install openpyxl
.venv/Scripts/python.exe -m pip freeze > requirements.txt
```
(주의: 기존 방식 그대로 freeze — requirements.txt는 dev 락파일 관례 유지)

- [ ] **Step 2: 실패하는 테스트 작성**

`tests/test_data_local.py`:
```python
import json

from teacher_widgets.core.data_local import (
    load_json_with_backup,
    save_json_with_backup,
)


def test_load_missing_returns_empty(tmp_path):
    assert load_json_with_backup(tmp_path / "a.json") == {}


def test_save_then_load_roundtrip_and_bak(tmp_path):
    p = tmp_path / "d" / "a.json"
    save_json_with_backup(p, {"v": 1})       # 최초 저장(부모 생성, bak 없음)
    assert not (tmp_path / "d" / "a.json.bak").exists()
    save_json_with_backup(p, {"v": 2})       # 두 번째 저장 → 이전본이 bak
    assert load_json_with_backup(p) == {"v": 2}
    assert json.loads((tmp_path / "d" / "a.json.bak").read_text(encoding="utf-8")) == {"v": 1}


def test_corrupt_recovers_from_bak(tmp_path):
    p = tmp_path / "a.json"
    save_json_with_backup(p, {"v": 1})
    save_json_with_backup(p, {"v": 2})
    p.write_text("{broken", encoding="utf-8")
    assert load_json_with_backup(p) == {"v": 1}  # bak 복구


def test_corrupt_without_bak_preserves_and_returns_empty(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("{broken", encoding="utf-8")
    assert load_json_with_backup(p) == {}
    corrupts = list(tmp_path.glob("a.corrupt-*.json"))
    assert len(corrupts) == 1
    assert corrupts[0].read_text(encoding="utf-8") == "{broken"
```

- [ ] **Step 3: RED 확인** — `.venv/Scripts/python.exe -m pytest tests/test_data_local.py -v` → ModuleNotFoundError

- [ ] **Step 4: 구현**

`src/teacher_widgets/core/data_local.py`:
```python
"""로컬 민감 데이터 파일 I/O: .bak 1세대 백업과 손상 복구.

출결·상담기록 등 학생 관련 데이터가 사용하는 공용 저장 계층.
이 모듈은 네트워크를 절대 사용하지 않는다.
"""

from __future__ import annotations

import datetime
import json
import shutil
from pathlib import Path


def load_json_with_backup(path: Path) -> dict:
    """JSON 로드. 손상 시 .bak 복구, 실패 시 손상본 보존 후 빈 dict."""
    path = Path(path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    bak = path.with_suffix(path.suffix + ".bak")
    if bak.exists():
        try:
            return json.loads(bak.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    # 복구 불가 — 데이터 소실 방지를 위해 손상본을 보존하고 빈 데이터로 시작
    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    corrupt = path.with_name(f"{path.stem}.corrupt-{ts}{path.suffix}")
    try:
        path.rename(corrupt)
    except OSError:
        pass
    return {}


def save_json_with_backup(path: Path, data: dict) -> None:
    """저장 전 기존 파일을 .bak으로 복사(1세대 백업)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
```

- [ ] **Step 5: GREEN + 전체 스위트** — 147 passed 예상 (143+4).

- [ ] **Step 6: 커밋**

```bash
git add src/teacher_widgets/core/data_local.py tests/test_data_local.py requirements.txt
git commit -m "feat: 로컬 민감 데이터 저장 계층(.bak 백업·손상 복구)과 openpyxl 추가

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: 기호표 + 출결 기록 헬퍼 (순수)

**Files:**
- Create: `src/teacher_widgets/widgets/attendance.py` (순수부 1)
- Test: `tests/test_attendance.py`

**Interfaces:**
- Consumes: (없음)
- Produces:
  - `STATUSES`, `REASONS`, `SYMBOLS: dict[tuple[str, str], str]` (16종), `symbol_for(status, reason) -> str`
  - `set_record(data: dict, date_iso: str, number: int, status: str, reason: str) -> None`
  - `clear_record(data: dict, date_iso: str, number: int) -> None` (빈 날짜 키 정리)
  - `get_record(data: dict, date_iso: str, number: int) -> dict | None`
  - `month_symbols(data: dict, year: int, month: int) -> dict[tuple[int, int], str]` — {(번호, 일): 기호}

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_attendance.py`:
```python
from teacher_widgets.widgets.attendance import (
    STATUSES,
    REASONS,
    SYMBOLS,
    symbol_for,
    set_record,
    clear_record,
    get_record,
    month_symbols,
)


def test_symbol_table_complete_16():
    assert STATUSES == ["결석", "지각", "조퇴", "결과"]
    assert REASONS == ["질병", "미인정", "기타", "출석인정"]
    assert len(SYMBOLS) == 16
    assert symbol_for("결석", "질병") == "♡"
    assert symbol_for("결석", "출석인정") == "△"  # 체험학습
    assert symbol_for("지각", "미인정") == "X"
    assert symbol_for("조퇴", "기타") == "∽"
    assert symbol_for("결과", "출석인정") == "▽"


def test_set_get_clear_record():
    data = {}
    set_record(data, "2026-07-03", 7, "결석", "질병")
    assert get_record(data, "2026-07-03", 7) == {"status": "결석", "reason": "질병"}
    assert data["records"]["2026-07-03"]["7"]["status"] == "결석"
    set_record(data, "2026-07-03", 7, "결석", "출석인정")  # 덮어쓰기
    assert get_record(data, "2026-07-03", 7)["reason"] == "출석인정"
    clear_record(data, "2026-07-03", 7)
    assert get_record(data, "2026-07-03", 7) is None
    assert "2026-07-03" not in data["records"]  # 빈 날짜 정리


def test_month_symbols():
    data = {}
    set_record(data, "2026-07-03", 7, "결석", "질병")
    set_record(data, "2026-07-15", 51, "지각", "출석인정")
    set_record(data, "2026-08-01", 7, "결석", "질병")  # 다른 달 — 제외
    out = month_symbols(data, 2026, 7)
    assert out == {(7, 3): "♡", (51, 15): "◁"}
```

- [ ] **Step 2: RED 확인** — ModuleNotFoundError

- [ ] **Step 3: 구현**

`src/teacher_widgets/widgets/attendance.py`:
```python
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
```

- [ ] **Step 4: GREEN + 전체 스위트** — 150 passed 예상.

- [ ] **Step 5: 커밋**

```bash
git add src/teacher_widgets/widgets/attendance.py tests/test_attendance.py
git commit -m "feat: 나이스 16기호표와 출결 기록 헬퍼

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: 자연어 명령 파서 (순수)

**Files:**
- Modify: `src/teacher_widgets/widgets/attendance.py`
- Test: `tests/test_attendance.py` (추가)

**Interfaces:**
- Consumes: Task 2의 STATUSES/REASONS.
- Produces: `parse_command(text: str, today: datetime.date, ref_year: int | None = None) -> dict | None`
  - 성공(기록): `{"number": int, "date": "YYYY-MM-DD" | None, "status": str, "reason": str}`
  - 성공(취소): `{"number": int, "date": "YYYY-MM-DD" | None, "clear": True}`
  - 실패: `None`. 날짜 연도 = `ref_year or today.year`.

- [ ] **Step 1: 실패하는 테스트 작성 (test_attendance.py에 추가)**

```python
import datetime

from teacher_widgets.widgets.attendance import parse_command

TODAY = datetime.date(2026, 7, 3)


def test_parse_full_command():
    assert parse_command("7번 6월 29일 결석", TODAY) == {
        "number": 7, "date": "2026-06-29", "status": "결석", "reason": "질병"}


def test_parse_no_date_returns_none_date():
    assert parse_command("5번 체험학습", TODAY) == {
        "number": 5, "date": None, "status": "결석", "reason": "출석인정"}


def test_parse_slash_and_dot_dates():
    assert parse_command("12번 7/1 미인정지각", TODAY)["date"] == "2026-07-01"
    assert parse_command("12번 7.1 미인정지각", TODAY)["status"] == "지각"
    assert parse_command("12번 7/1 미인정지각", TODAY)["reason"] == "미인정"


def test_parse_prefix_modifiers():
    assert parse_command("3번 인정조퇴", TODAY) == {
        "number": 3, "date": None, "status": "조퇴", "reason": "출석인정"}
    assert parse_command("3번 기타결과", TODAY)["reason"] == "기타"
    assert parse_command("3번 질병결석", TODAY)["reason"] == "질병"


def test_parse_clear():
    assert parse_command("7번 6월 29일 취소", TODAY) == {
        "number": 7, "date": "2026-06-29", "clear": True}
    assert parse_command("7번 지우기", TODAY) == {
        "number": 7, "date": None, "clear": True}


def test_parse_ref_year():
    assert parse_command("7번 1월 5일 결석", TODAY, ref_year=2027)["date"] == "2027-01-05"


def test_parse_failures():
    assert parse_command("결석", TODAY) is None            # 번호 없음
    assert parse_command("7번", TODAY) is None             # 출결어 없음
    assert parse_command("7번 낮잠", TODAY) is None        # 미지의 단어
    assert parse_command("", TODAY) is None
```

- [ ] **Step 2: RED 확인** — ImportError: parse_command

- [ ] **Step 3: 구현 (attendance.py에 추가)**

```python
import datetime
import re

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
```

- [ ] **Step 4: GREEN + 전체 스위트** — 157 passed 예상.

- [ ] **Step 5: 커밋**

```bash
git add src/teacher_widgets/widgets/attendance.py tests/test_attendance.py
git commit -m "feat: 출결 자연어 명령 파서(날짜·수식접두·취소)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Excel 빌더 (openpyxl, 순수)

**Files:**
- Modify: `src/teacher_widgets/widgets/attendance.py`
- Test: `tests/test_attendance.py` (추가)

**Interfaces:**
- Consumes: Task 2의 SYMBOLS/month_symbols.
- Produces:
  - `months_with_records(data: dict) -> list[str]` — 정렬된 "YYYY-MM" 목록.
  - `build_attendance_workbook(data: dict, numbers: list[int], months: list[str]) -> openpyxl.Workbook` — 월당 시트 1개. 시트명 "YYYY-MM". 1행 제목 "YYYY년 M월 출결", 2행 범례(16종 "결석 질병♡ …" 한 줄 문자열), 4행 헤더 ["번호", 1..말일], 5행부터 번호별 행(기호). 주말 열은 헤더 셀 회색 채움(PatternFill "DDDDDD").

- [ ] **Step 1: 실패하는 테스트 작성 (test_attendance.py에 추가)**

```python
from teacher_widgets.widgets.attendance import (
    build_attendance_workbook,
    months_with_records,
)


def _sample_data():
    data = {}
    set_record(data, "2026-07-03", 7, "결석", "질병")
    set_record(data, "2026-07-15", 51, "결석", "출석인정")
    set_record(data, "2026-06-29", 7, "지각", "질병")
    return data


def test_months_with_records():
    assert months_with_records(_sample_data()) == ["2026-06", "2026-07"]
    assert months_with_records({}) == []


def test_workbook_single_month():
    wb = build_attendance_workbook(_sample_data(), [7, 51], ["2026-07"])
    assert wb.sheetnames == ["2026-07"]
    ws = wb["2026-07"]
    assert "2026년 7월" in ws.cell(row=1, column=1).value
    assert "♡" in ws.cell(row=2, column=1).value  # 범례
    assert ws.cell(row=4, column=1).value == "번호"
    assert ws.cell(row=4, column=32).value == 31  # 7월 말일
    # 5행=번호7, 6행=번호51; 날짜 d는 열 d+1
    assert ws.cell(row=5, column=1).value == 7
    assert ws.cell(row=5, column=4).value == "♡"    # 7/3
    assert ws.cell(row=6, column=16).value == "△"   # 51번 7/15
    assert ws.cell(row=5, column=5).value in (None, "")


def test_workbook_multi_month_and_weekend_fill():
    wb = build_attendance_workbook(_sample_data(), [7], ["2026-06", "2026-07"])
    assert wb.sheetnames == ["2026-06", "2026-07"]
    ws = wb["2026-07"]
    # 2026-07-04는 토요일 → 헤더 열 5 회색 채움
    assert ws.cell(row=4, column=5).fill.start_color.rgb.endswith("DDDDDD")
    # 평일(7/3 금) 헤더는 채움 없음(기본 00000000)
    assert not str(ws.cell(row=4, column=4).fill.start_color.rgb).endswith("DDDDDD")
```

- [ ] **Step 2: RED 확인** — ImportError

- [ ] **Step 3: 구현 (attendance.py에 추가)**

```python
import calendar

from openpyxl import Workbook
from openpyxl.styles import PatternFill

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
```

- [ ] **Step 4: GREEN + 전체 스위트** — 160 passed 예상.

- [ ] **Step 5: 커밋**

```bash
git add src/teacher_widgets/widgets/attendance.py tests/test_attendance.py
git commit -m "feat: 출결 Excel 빌더(월별 시트·범례·주말 음영)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: AttendanceWidget (GUI)

**Files:**
- Modify: `src/teacher_widgets/widgets/attendance.py`
- Test: `tests/test_attendance.py` (추가)

**Interfaces:**
- Consumes: Task 1 `data_local`, Task 2~4 순수부, `BaseWidget`(`_custom_menu_actions` 훅), `ConfigStore.get_roster`, `roster_numbers`, `responsive`.
- Produces: `class AttendanceWidget(BaseWidget)` (widget_name="attendance", BASE_SIZE=(520, 420))
  - `data_path: Path` (store.path.parent / "attendance.json"), `_data: dict`
  - `_year/_month: int` (초기 오늘), `go_month(delta: int)` (◀▶), `month_label: QLabel`
  - `table: QTableWidget` — 행=roster 번호, 열=1~말일, 셀=기호, 주말 열 배경 회색; `rebuild_table()`
  - `cell_symbol(number: int, day: int) -> str` (테스트 접근자)
  - `apply_record(number, date_iso, status, reason)` / `apply_clear(number, date_iso)` — 데이터 갱신+저장+해당 셀 갱신
  - `handle_command_text(text: str) -> bool` — parse→(날짜 없으면 오늘 확인: `_confirm_today()` 훅, 기본 QMessageBox, 테스트에서 오버라이드)→apply. 실패 시 `error_label` 표시 후 False.
  - `command_edit: QLineEdit`, `error_label: QLabel`
  - 셀 클릭 퀵메뉴(`_cell_menu`): 결석♡/체험학습△/지각▸/조퇴▸/결과▸/결석 상세▸(사유 서브)/지우기
  - `_custom_menu_actions`: "Excel 내보내기(현재 월)" / "Excel 내보내기(전체)" → `export_excel(all_months: bool)` (QFileDialog — 얇게, 테스트 제외; 워크북 생성은 Task 4 순수 함수)

- [ ] **Step 1: 실패하는 테스트 작성 (test_attendance.py에 추가)**

```python
import json as _json

from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.widgets.attendance import AttendanceWidget


def make_widget(qtbot, tmp_path, boys=3, girls=2):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    store.set_roster(boys, girls)
    w = AttendanceWidget(store)
    qtbot.addWidget(w)
    return store, w


def test_widget_table_shape_from_roster(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path)  # 번호 1,2,3,51,52
    assert w.widget_name == "attendance"
    assert w.table.rowCount() == 5
    nums = [int(w.table.verticalHeaderItem(r).text()) for r in range(5)]
    assert nums == [1, 2, 3, 51, 52]


def test_apply_record_updates_cell_and_file(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path)
    date_iso = f"{w._year:04d}-{w._month:02d}-03"
    w.apply_record(2, date_iso, "결석", "질병")
    assert w.cell_symbol(2, 3) == "♡"
    saved = _json.loads((tmp_path / "attendance.json").read_text(encoding="utf-8"))
    assert saved["records"][date_iso]["2"]["status"] == "결석"
    w.apply_clear(2, date_iso)
    assert w.cell_symbol(2, 3) == ""


def test_handle_command_with_explicit_date(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path)
    assert w.handle_command_text(f"3번 {w._month}월 5일 체험학습") is True
    assert w.cell_symbol(3, 5) == "△"


def test_handle_command_today_confirm(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path)
    w._confirm_today = lambda: True  # 팝업 우회
    import datetime as _dt
    today = _dt.date.today()
    w._year, w._month = today.year, today.month
    w.rebuild_table()
    assert w.handle_command_text("51번 결석") is True
    assert w.cell_symbol(51, today.day) == "♡"


def test_handle_command_rejects_unknown_number_and_garbage(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path)
    assert w.handle_command_text("9번 결석") is False   # roster 밖(1-3,51-52)
    assert w.error_label.text() != ""
    assert w.handle_command_text("염소") is False


def test_month_navigation(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path)
    w._year, w._month = 2026, 1
    w.rebuild_table()
    assert w.table.columnCount() == 31
    w.go_month(1)   # 2월
    assert (w._year, w._month) == (2026, 2)
    assert w.table.columnCount() == 28
    w.go_month(-2)  # 12월로 롤백
    assert (w._year, w._month) == (2025, 12)
```

- [ ] **Step 2: RED 확인** — ImportError: AttendanceWidget

- [ ] **Step 3: 구현 (attendance.py에 추가)**

import 보강:
```python
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from teacher_widgets.core.base_widget import BaseWidget
from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.core.data_local import (
    load_json_with_backup,
    save_json_with_backup,
)
from teacher_widgets.core.responsive import scale_factor, scaled_font_pt
from teacher_widgets.core.roster import roster_numbers
```

클래스:
```python
class AttendanceWidget(BaseWidget):
    BASE_SIZE = (520, 420)

    def __init__(self, store: ConfigStore):
        super().__init__("attendance", store)
        self.data_path = Path(store.path).parent / "attendance.json"
        self._data = load_json_with_backup(self.data_path)
        today = datetime.date.today()
        self._year, self._month = today.year, today.month

        # 상단: ◀ 2026년 7월 ▶
        nav = QtWidgets.QHBoxLayout()
        prev_btn = QtWidgets.QPushButton("◀")
        next_btn = QtWidgets.QPushButton("▶")
        prev_btn.setFixedWidth(28)
        next_btn.setFixedWidth(28)
        prev_btn.clicked.connect(lambda: self.go_month(-1))
        next_btn.clicked.connect(lambda: self.go_month(1))
        self.month_label = QtWidgets.QLabel("", alignment=QtCore.Qt.AlignCenter)
        self.month_label.setStyleSheet("font-weight:700; color:#2b2b2b;")
        nav.addWidget(prev_btn)
        nav.addWidget(self.month_label, stretch=1)
        nav.addWidget(next_btn)
        self.content_layout.addLayout(nav)

        # 그리드
        self.table = QtWidgets.QTableWidget()
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.table.verticalHeader().setDefaultSectionSize(20)
        self.table.horizontalHeader().setDefaultSectionSize(24)
        self.table.cellClicked.connect(self._on_cell_clicked)
        self.content_layout.addWidget(self.table, stretch=1)

        # 자연어 입력줄
        self.command_edit = QtWidgets.QLineEdit()
        self.command_edit.setPlaceholderText("예: 7번 6월 29일 결석 · 5번 체험학습 · 7번 취소")
        self.command_edit.returnPressed.connect(self._on_command_entered)
        self.content_layout.addWidget(self.command_edit)
        self.error_label = QtWidgets.QLabel("")
        self.error_label.setStyleSheet("color:#c0392b;")
        self.content_layout.addWidget(self.error_label)

        self.rebuild_table()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(QtGui.QColor(255, 255, 255, 240))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 16, 16)

    # --- 번호/월 ---
    def _numbers(self) -> list[int]:
        boys, girls = self.store.get_roster()
        return roster_numbers(boys, girls)

    def go_month(self, delta: int) -> None:
        month = self._month + delta
        year = self._year
        while month < 1:
            month += 12
            year -= 1
        while month > 12:
            month -= 12
            year += 1
        self._year, self._month = year, month
        self.rebuild_table()

    # --- 그리드 ---
    def rebuild_table(self) -> None:
        numbers = self._numbers()
        last_day = calendar.monthrange(self._year, self._month)[1]
        self.month_label.setText(f"{self._year}년 {self._month}월")
        self.table.clear()
        self.table.setRowCount(len(numbers))
        self.table.setColumnCount(last_day)
        self.table.setHorizontalHeaderLabels([str(d) for d in range(1, last_day + 1)])
        self.table.setVerticalHeaderLabels([str(n) for n in numbers])
        weekend_brush = QtGui.QBrush(QtGui.QColor("#eeeeee"))
        symbols = month_symbols(self._data, self._year, self._month)
        for row, number in enumerate(numbers):
            for day in range(1, last_day + 1):
                item = QtWidgets.QTableWidgetItem(symbols.get((number, day), ""))
                item.setTextAlignment(QtCore.Qt.AlignCenter)
                if datetime.date(self._year, self._month, day).weekday() >= 5:
                    item.setBackground(weekend_brush)
                self.table.setItem(row, day - 1, item)

    def cell_symbol(self, number: int, day: int) -> str:
        row = self._numbers().index(number)
        item = self.table.item(row, day - 1)
        return item.text() if item else ""

    # --- 기록 적용 ---
    def _save(self) -> None:
        save_json_with_backup(self.data_path, self._data)

    def _refresh_cell(self, number: int, date_iso: str) -> None:
        if not date_iso.startswith(f"{self._year:04d}-{self._month:02d}-"):
            return  # 다른 달 — 현재 그리드 무관
        day = int(date_iso[8:10])
        rec = get_record(self._data, date_iso, number)
        text = symbol_for(rec["status"], rec["reason"]) if rec else ""
        row = self._numbers().index(number)
        item = self.table.item(row, day - 1)
        if item:
            item.setText(text)

    def apply_record(self, number: int, date_iso: str, status: str, reason: str) -> None:
        set_record(self._data, date_iso, number, status, reason)
        self._save()
        self._refresh_cell(number, date_iso)

    def apply_clear(self, number: int, date_iso: str) -> None:
        clear_record(self._data, date_iso, number)
        self._save()
        self._refresh_cell(number, date_iso)

    # --- 자연어 입력 ---
    def _confirm_today(self) -> bool:
        """날짜 생략 시 '오늘로 기록할까요?' 확인. 테스트에서 오버라이드."""
        today = datetime.date.today()
        answer = QtWidgets.QMessageBox.question(
            self, "확인", f"오늘({today.month}/{today.day})로 기록할까요?")
        return answer == QtWidgets.QMessageBox.Yes

    def handle_command_text(self, text: str) -> bool:
        self.error_label.setText("")
        cmd = parse_command(text, datetime.date.today(), ref_year=self._year)
        if cmd is None:
            self.error_label.setText("이해하지 못했어요 — 예: 7번 6월 29일 결석")
            return False
        if cmd["number"] not in self._numbers():
            self.error_label.setText(f"{cmd['number']}번은 학급 구성에 없습니다")
            return False
        date_iso = cmd["date"]
        if date_iso is None:
            if not self._confirm_today():
                return False
            date_iso = datetime.date.today().isoformat()
        if cmd.get("clear"):
            self.apply_clear(cmd["number"], date_iso)
        else:
            self.apply_record(cmd["number"], date_iso, cmd["status"], cmd["reason"])
        return True

    def _on_command_entered(self) -> None:
        if self.handle_command_text(self.command_edit.text()):
            self.command_edit.clear()

    # --- 셀 퀵메뉴 ---
    def _on_cell_clicked(self, row: int, col: int) -> None:
        number = self._numbers()[row]
        date_iso = f"{self._year:04d}-{self._month:02d}-{col + 1:02d}"
        menu = QtWidgets.QMenu(self)
        quick = [("결석 ♡", "결석", "질병"), ("체험학습 △", "결석", "출석인정")]
        for label, status, reason in quick:
            menu.addAction(label, lambda s=status, r=reason:
                           self.apply_record(number, date_iso, s, r))
        menu.addSeparator()
        detail_status = [("결석 상세", "결석"), ("지각", "지각"),
                         ("조퇴", "조퇴"), ("결과", "결과")]
        for label, status in detail_status:
            sub = menu.addMenu(label)
            for reason in REASONS:
                sub.addAction(
                    f"{reason} {symbol_for(status, reason)}",
                    lambda s=status, r=reason:
                    self.apply_record(number, date_iso, s, r))
        menu.addSeparator()
        menu.addAction("지우기", lambda: self.apply_clear(number, date_iso))
        menu.exec(QtGui.QCursor.pos())

    # --- Excel ---
    def export_excel(self, all_months: bool) -> None:
        months = (months_with_records(self._data) if all_months
                  else [f"{self._year:04d}-{self._month:02d}"])
        if not months:
            self.error_label.setText("내보낼 기록이 없습니다")
            return
        default = f"출결_{months[0]}{'_전체' if all_months else ''}.xlsx"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Excel로 내보내기", default, "Excel (*.xlsx)")
        if not path:
            return
        try:
            wb = build_attendance_workbook(self._data, self._numbers(), months)
            wb.save(path)
            self.error_label.setStyleSheet("color:#2b6e4f;")
            self.error_label.setText(f"저장됨: {path}")
        except OSError as exc:
            self.error_label.setStyleSheet("color:#c0392b;")
            self.error_label.setText(f"저장 실패: {exc}")

    def _custom_menu_actions(self, menu) -> dict:
        cur = menu.addAction("Excel 내보내기(현재 월)")
        full = menu.addAction("Excel 내보내기(전체)")
        return {cur: lambda: self.export_excel(False),
                full: lambda: self.export_excel(True)}

    # --- 반응형 ---
    def _apply_responsive(self) -> None:
        factor = scale_factor((self.width(), self.height()), self.BASE_SIZE)
        self.month_label.setStyleSheet(
            f"font-weight:700; color:#2b2b2b; font-size:{scaled_font_pt(12, factor)}pt;")
        font = self.table.font()
        font.setPointSize(scaled_font_pt(9, factor))
        self.table.setFont(font)

    def on_resized(self, width: int, height: int) -> None:
        self._apply_responsive()
```

- [ ] **Step 4: GREEN + 전체 스위트** — 166 passed 예상.

- [ ] **Step 5: 커밋**

```bash
git add src/teacher_widgets/widgets/attendance.py tests/test_attendance.py
git commit -m "feat: 출결 위젯(월 그리드·퀵메뉴·자연어 입력·Excel 내보내기)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: 런처 등록 + 스모크

**Files:**
- Modify: `src/teacher_widgets/main.py`
- Test: `tests/test_tray.py` (1개 추가)

- [ ] **Step 1: 테스트 (test_tray.py에 추가 — 즉시 통과 예상)**

```python
def test_tray_menu_lists_attendance(qtbot, tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    reg = WidgetRegistry(store)
    reg.register("attendance", lambda: BaseWidget("attendance", store))
    menu = build_tray_menu(reg)
    assert "attendance" in [a.text() for a in menu.actions() if a.text()]
```

- [ ] **Step 2: main.py 등록**

import: `from .widgets.attendance import AttendanceWidget`
weather 등록 다음: `registry.register("attendance", lambda: AttendanceWidget(store))`

- [ ] **Step 3: 전체 스위트** — 167 passed 예상.

- [ ] **Step 4: 비차단 구성 스모크**

```bash
QT_QPA_PLATFORM=offscreen PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "
import sys, tempfile, os; sys.path.insert(0, 'src')
from PySide6 import QtWidgets
app = QtWidgets.QApplication([])
from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.widgets.attendance import AttendanceWidget
d = tempfile.mkdtemp(); s = ConfigStore(os.path.join(d, 'c.json')); s.load()
w = AttendanceWidget(s)
w.apply_record(1, f'{w._year:04d}-{w._month:02d}-01', '결석', '질병')
print('OK', w.widget_name, 'cell:', w.cell_symbol(1, 1),
      'file:', os.path.exists(os.path.join(d, 'attendance.json')))
"
```
Expected: `OK attendance cell: ♡ file: True`

- [ ] **Step 5: 커밋**

```bash
git add src/teacher_widgets/main.py tests/test_tray.py
git commit -m "feat: 런처에 출결 위젯 등록

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 자기 점검 (Self-Review)

**1. Spec 커버리지:** 16기호표(§2)→T2 / attendance.json 구조·번호 문자열 키(§2)→T2·T5 / .bak 백업·손상 복구·corrupt 보존(§2·§8)→T1 / roster 재사용(§2)→T5 / 월 그리드·주말 음영·◀▶(§3)→T5 / 셀 퀵메뉴 구성(§3)→T5 / 자연어 문법 전체(§4: 날짜 3형·접두·취소·roster 검증·실패 안내·오늘 확인 팝업)→T3·T5 / Excel 시트 구성·범례·주말 채움·현재/전체(§5)→T4·T5 / QFileDialog 저장·실패 안내(§5·§8)→T5 / openpyxl(§5)→T1 / 윤년·월말일(§8)→T5 test_month_navigation(2026-02=28일) / roster 축소 데이터 보존(§8)→구조상 자동(기록은 파일에, 그리드는 roster만) / 등록(§6)→T6 ✅
**2. 플레이스홀더:** 없음 ✅
**3. 타입 일관성:** `set_record(data,date_iso,number:int,...)` 내부 str(number) 저장 / `month_symbols->{(int,int):str}` / `parse_command->dict|None` / `cell_symbol(number,day)->str` / `build_attendance_workbook(data,numbers:list[int],months:list[str])` — Task 간 일치 ✅
**범위 밖:** 수업일수 계산, 상담기록(4-C).
