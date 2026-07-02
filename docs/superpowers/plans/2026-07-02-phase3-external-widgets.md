# Phase 3 외부형 위젯 3종 구현 계획 (주간학습계획 · 급식 · 날씨)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Firestore(주간학습계획)·나이스(급식)·Open-Meteo(날씨)를 읽는 외부형 위젯 3종을 Phase 2에서 확립한 패턴(data_remote, FetchWorker, show/hide 타이머, 캐시) 위에 얹는다.

**Architecture:** `data_remote`에 공용 SSL 컨텍스트(strict 완화)·`http_get_json`·`firestore_run_query`를 추가한다. 각 위젯은 [순수 함수(URL/질의 생성·파싱·매핑) + Worker(QThread) + Widget(BaseWidget)] 3층으로, 순수 함수는 실측 형태 픽스처로 테스트하고 위젯은 캐시 주입으로 테스트한다. 주간학습계획은 Phase 0의 `resolve_breakpoint`를 최초 실전 적용한다.

**Tech Stack:** Python 3.14, PySide6, stdlib urllib/ssl, pytest + pytest-qt.

## Global Constraints

- Python 3.14.x. PySide6 Widgets. 새 pip 의존성 금지. 테스트에서 실제 네트워크 금지(실측은 마지막 스모크 1회).
- 테스트: `QT_QPA_PLATFORM=offscreen` 헤드리스. 실행 `.venv/Scripts/python.exe -m pytest -v` (경로 공백·한글 → 따옴표).
- 캐시: `store.path.parent / "cache" / "<widget>.json"`. config.json에 데이터 저장 금지.
- 위젯 공통 수명주기(시간표와 동일): `__init__`에서 타이머 생성만(시작 금지)·`aboutToQuit→_shutdown_worker(wait 2000ms)` 연결, `showEvent`에서 타이머 시작+`_skip_initial_fetch` 가드 하 refresh, `hideEvent`에서 타이머 정지. 실패 시 상태 라벨 "갱신 실패 — 캐시 표시 중" + `setToolTip(msg)`.
- config 기본값(정확히):
  - `weekly_plan`: api_key `AIzaSyA2R8xghbMYtVDvo1D0QbxKnfDSwoSPszU`, project_id `sunil-edu-plan`, artifact_app_id `sunil-edu-plan`, webapp_url `https://sunil-edu-plan.vercel.app/`, refresh_minutes 30
  - `meal`: edu_code `B10`, school_code `7031170`, api_key `""`, refresh_minutes 360
  - `weather`: lat 37.617, lon 126.921, refresh_minutes 30
- Firestore 문서형: schedules `{date:"YYYY-MM-DD", department, content, order?}` / weekly_messages `{principal, vicePrincipal, journal}`. weekId = 이번 주 월요일 ISO.
- 나이스 급식 필드: `DDISH_NM`(`<br/>` 구분, 항목 끝 `(2.4.5)` 알레르기), `CAL_INFO`, `MLSV_YMD`. 데이터 없음 = `RESULT.CODE == "INFO-200"`.
- 등급표: PM10 좋음≤30/보통≤80/나쁨≤150/매우나쁨>150; PM2.5 좋음≤15/보통≤35/나쁨≤75/매우나쁨>75.
- 위젯 식별자: `weekly_plan`, `meal`, `weather`.
- BaseWidget 멤버: `__init__(widget_name, store)`, `content_layout`, `BASE_SIZE`, `on_resized(w,h)`, `_custom_menu_actions(menu)->dict`.
- responsive: `scale_factor((w,h),BASE_SIZE)`, `scaled_font_pt(pt,factor)`, `resolve_breakpoint(value, [(threshold,label),...])`.
- data_remote 기존: `anon_sign_in(api_key)`, `firestore_get_document(project_id, doc_path, id_token)`, `read_cache(path)`, `write_cache(path,data)`.
- 시간표 참조 구현: `widgets/timetable.py`의 `FetchWorker`/`TimetableWidget`(showEvent/hideEvent/_shutdown_worker/refresh/_on_fetch_ok/_on_fetch_failed/build_app_command/open_webapp/_bring_web_to_front) — 동일 패턴을 각 위젯에 적용하되 파일 간 복붙 최소화를 위해 웹앱 실행 함수는 timetable에서 import 재사용.
- 커밋 footer: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. 기존 103 테스트 유지.

---

## 파일 구조

```
src/teacher_widgets/
├─ core/data_remote.py      # (수정) _ssl_context, http_get_json, firestore_run_query
├─ core/config_store.py     # (수정) weekly_plan/meal/weather 기본값
├─ widgets/weekly_plan.py   # (신규) 순수 + PlanFetchWorker + WeeklyPlanWidget
├─ widgets/meal.py          # (신규) 순수 + MealFetchWorker + MealWidget
├─ widgets/weather.py       # (신규) 순수 + WeatherFetchWorker + WeatherWidget
└─ main.py                  # (수정) 3종 등록
tests/
├─ test_data_remote.py      # (수정) ssl context·run_query 파싱 테스트 추가
├─ test_config_store.py     # (수정) 기본값 테스트 추가
├─ test_weekly_plan.py      # (신규)
├─ test_meal.py             # (신규)
└─ test_weather.py          # (신규)
```

---

## Task 1: data_remote 확장 + config 기본값

**Files:**
- Modify: `src/teacher_widgets/core/data_remote.py`
- Modify: `src/teacher_widgets/core/config_store.py`
- Test: `tests/test_data_remote.py`, `tests/test_config_store.py`

**Interfaces:**
- Consumes: 기존 data_remote 함수들.
- Produces:
  - `_ssl_context() -> ssl.SSLContext` (모듈 캐시; 체인 검증 유지, `VERIFY_X509_STRICT`만 해제)
  - `http_get_json(url: str, headers: dict | None = None, timeout: int = 20) -> dict`
  - `firestore_run_query(project_id: str, parent_path: str, structured_query: dict, id_token: str, timeout: int = 30) -> list[dict]` — `POST https://firestore.googleapis.com/v1/projects/{pid}/databases/(default)/documents/{parent_path}:runQuery`, body `{"structuredQuery": structured_query}`, 응답 행 중 `"document"` 키가 있는 것만 리스트로.
  - 기존 `anon_sign_in`/`firestore_get_document`도 내부에서 `_ssl_context()` 사용.
  - `DEFAULT_CONFIG`에 `weekly_plan`/`meal`/`weather` 키(Global Constraints의 값 그대로).

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_data_remote.py`에 추가:
```python
import ssl

from teacher_widgets.core.data_remote import _ssl_context, _rows_to_documents


def test_ssl_context_relaxes_strict_only():
    ctx = _ssl_context()
    assert ctx.verify_mode == ssl.CERT_REQUIRED  # 체인 검증은 유지
    assert not (ctx.verify_flags & ssl.VERIFY_X509_STRICT)  # strict만 해제
    assert _ssl_context() is ctx  # 모듈 캐시


def test_rows_to_documents_filters_non_document_rows():
    rows = [
        {"readTime": "..."},  # 문서 없는 메타 행
        {"document": {"name": "d1", "fields": {"date": {"stringValue": "2026-07-02"}}}},
        {"document": {"name": "d2", "fields": {}}},
    ]
    docs = _rows_to_documents(rows)
    assert [d["name"] for d in docs] == ["d1", "d2"]
```

`tests/test_config_store.py`에 추가:
```python
def test_default_phase3_settings(tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    assert store.data["weekly_plan"]["project_id"] == "sunil-edu-plan"
    assert store.data["weekly_plan"]["refresh_minutes"] == 30
    assert store.data["meal"]["edu_code"] == "B10"
    assert store.data["meal"]["school_code"] == "7031170"
    assert store.data["meal"]["api_key"] == ""
    assert store.data["weather"]["lat"] == 37.617
    assert store.data["weather"]["refresh_minutes"] == 30
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `.venv/Scripts/python.exe -m pytest tests/test_data_remote.py tests/test_config_store.py -v`
Expected: FAIL (ImportError `_ssl_context` / KeyError `weekly_plan`)

- [ ] **Step 3: 구현**

`data_remote.py` — import에 `import ssl` 추가, 파일 상단에:
```python
_CTX: ssl.SSLContext | None = None


def _ssl_context() -> ssl.SSLContext:
    """공용 SSL 컨텍스트: 체인 검증은 유지하되 X509 strict만 해제.

    Python 3.13+ 기본 VERIFY_X509_STRICT가 나이스 등 정부 인증서
    (Authority Key Identifier 누락)를 거부하는 문제의 우회.
    """
    global _CTX
    if _CTX is None:
        _CTX = ssl.create_default_context()
        _CTX.verify_flags &= ~ssl.VERIFY_X509_STRICT
    return _CTX


def http_get_json(url: str, headers: dict | None = None, timeout: int = 20) -> dict:
    """공용 GET(JSON). 정부 API 대응 컨텍스트 사용."""
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as r:
        return json.load(r)


def _rows_to_documents(rows: list) -> list[dict]:
    """runQuery 응답 행에서 document만 추출(순수 — 테스트 대상)."""
    return [row["document"] for row in rows if "document" in row]


def firestore_run_query(
    project_id: str,
    parent_path: str,
    structured_query: dict,
    id_token: str,
    timeout: int = 30,
) -> list[dict]:
    """Firestore REST :runQuery — document 행만 반환."""
    url = (
        f"https://firestore.googleapis.com/v1/projects/{project_id}"
        f"/databases/(default)/documents/{parent_path}:runQuery"
    )
    req = urllib.request.Request(
        url,
        data=json.dumps({"structuredQuery": structured_query}).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {id_token}",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as r:
        return _rows_to_documents(json.load(r))
```

기존 `anon_sign_in`·`firestore_get_document`의 `urlopen(...)` 호출에 `context=_ssl_context()` 인자 추가.

`config_store.py` `DEFAULT_CONFIG`에 (timetable 아래):
```python
    "weekly_plan": {
        "api_key": "AIzaSyA2R8xghbMYtVDvo1D0QbxKnfDSwoSPszU",
        "project_id": "sunil-edu-plan",
        "artifact_app_id": "sunil-edu-plan",
        "webapp_url": "https://sunil-edu-plan.vercel.app/",
        "refresh_minutes": 30,
    },
    "meal": {
        "edu_code": "B10",
        "school_code": "7031170",
        "api_key": "",
        "refresh_minutes": 360,
    },
    "weather": {
        "lat": 37.617,
        "lon": 126.921,
        "refresh_minutes": 30,
    },
```

- [ ] **Step 4: 테스트 통과 확인 + 전체 스위트**

Run: `.venv/Scripts/python.exe -m pytest -q` → 106 passed 예상 (103+3).

- [ ] **Step 5: 커밋**

```bash
git add src/teacher_widgets/core/data_remote.py src/teacher_widgets/core/config_store.py tests/test_data_remote.py tests/test_config_store.py
git commit -m "feat: data_remote SSL 완화·runQuery·공용 GET과 Phase3 설정 기본값

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: 주간학습계획 순수 함수

**Files:**
- Create: `src/teacher_widgets/widgets/weekly_plan.py` (순수부)
- Test: `tests/test_weekly_plan.py`

**Interfaces:**
- Consumes: (없음 — 순수)
- Produces:
  - `week_monday(today: datetime.date) -> datetime.date` (주말이면 다음 주 월요일)
  - `build_schedules_query(start_iso: str, end_iso: str) -> dict` (runQuery용 structuredQuery: schedules, date 범위, date ASC, limit 200)
  - `parse_schedule_docs(docs: list[dict]) -> list[dict]` → `[{date, department, content, order}]` (order 없으면 0)
  - `parse_messages_doc(fs_doc: dict) -> dict` → `{"principal": str, "vicePrincipal": str}` (빈 문서/None 허용)
  - `group_entries(entries: list) -> dict[str, list]` (date→항목들, 각 날짜 내 학사일정 먼저 그 다음 order 오름차순)
  - `pick_days(tier: str, base_monday: datetime.date, today: datetime.date) -> list[datetime.date]` — compact: [오늘(주말이면 base_monday)], two_days: 그 날+다음 날, week: base_monday~금 + 다음 주 월
  - `PLAN_TIERS = [(0, "compact"), (300, "two_days"), (480, "week")]`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_weekly_plan.py`:
```python
import datetime

from teacher_widgets.widgets.weekly_plan import (
    week_monday,
    build_schedules_query,
    parse_schedule_docs,
    parse_messages_doc,
    group_entries,
    pick_days,
    PLAN_TIERS,
)


def _doc(date, dept, content, order=None):
    fields = {
        "date": {"stringValue": date},
        "department": {"stringValue": dept},
        "content": {"stringValue": content},
    }
    if order is not None:
        fields["order"] = {"integerValue": str(order)}
    return {"name": f"doc-{date}-{dept}", "fields": fields}


def test_week_monday_weekday_and_weekend():
    assert week_monday(datetime.date(2026, 7, 2)) == datetime.date(2026, 6, 29)  # 목
    assert week_monday(datetime.date(2026, 7, 4)) == datetime.date(2026, 7, 6)   # 토→다음주 월
    assert week_monday(datetime.date(2026, 7, 5)) == datetime.date(2026, 7, 6)   # 일→다음주 월


def test_build_schedules_query_shape():
    q = build_schedules_query("2026-06-29", "2026-07-06")
    assert q["from"] == [{"collectionId": "schedules"}]
    filters = q["where"]["compositeFilter"]["filters"]
    assert filters[0]["fieldFilter"]["op"] == "GREATER_THAN_OR_EQUAL"
    assert filters[0]["fieldFilter"]["value"]["stringValue"] == "2026-06-29"
    assert filters[1]["fieldFilter"]["op"] == "LESS_THAN_OR_EQUAL"
    assert q["limit"] == 200


def test_parse_schedule_docs():
    docs = [_doc("2026-06-29", "행정실", "체육관 사용 안내", 5),
            _doc("2026-06-29", "학사일정", "기말평가주간")]
    out = parse_schedule_docs(docs)
    assert out[0] == {"date": "2026-06-29", "department": "행정실",
                      "content": "체육관 사용 안내", "order": 5}
    assert out[1]["order"] == 0


def test_parse_messages_doc():
    doc = {"fields": {"principal": {"stringValue": "안전 제일"},
                      "vicePrincipal": {"stringValue": "수고 많으십니다"}}}
    assert parse_messages_doc(doc) == {"principal": "안전 제일",
                                       "vicePrincipal": "수고 많으십니다"}
    assert parse_messages_doc(None) == {"principal": "", "vicePrincipal": ""}
    assert parse_messages_doc({}) == {"principal": "", "vicePrincipal": ""}


def test_group_entries_hakssa_first_then_order():
    entries = [
        {"date": "2026-06-29", "department": "행정실", "content": "b", "order": 1},
        {"date": "2026-06-29", "department": "학사일정", "content": "a", "order": 99},
        {"date": "2026-06-29", "department": "교육과정부", "content": "c", "order": 0},
        {"date": "2026-06-30", "department": "5학년", "content": "d", "order": 0},
    ]
    g = group_entries(entries)
    assert [e["content"] for e in g["2026-06-29"]] == ["a", "c", "b"]
    assert [e["content"] for e in g["2026-06-30"]] == ["d"]


def test_pick_days_tiers():
    mon = datetime.date(2026, 6, 29)
    thu = datetime.date(2026, 7, 2)
    assert pick_days("compact", mon, thu) == [thu]
    assert pick_days("two_days", mon, thu) == [thu, datetime.date(2026, 7, 3)]
    week = pick_days("week", mon, thu)
    assert week[0] == mon and week[-1] == datetime.date(2026, 7, 6) and len(week) == 6


def test_pick_days_weekend_uses_base_monday():
    sat = datetime.date(2026, 7, 4)
    mon = week_monday(sat)  # 2026-07-06
    assert pick_days("compact", mon, sat) == [mon]


def test_plan_tiers_shape():
    assert PLAN_TIERS == [(0, "compact"), (300, "two_days"), (480, "week")]
```

- [ ] **Step 2: RED 확인**

Run: `.venv/Scripts/python.exe -m pytest tests/test_weekly_plan.py -v` → ModuleNotFoundError

- [ ] **Step 3: 구현**

`src/teacher_widgets/widgets/weekly_plan.py`:
```python
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
```

- [ ] **Step 4: GREEN + 전체 스위트**

Run: `.venv/Scripts/python.exe -m pytest -q` → 114 passed 예상 (106+8).

- [ ] **Step 5: 커밋**

```bash
git add src/teacher_widgets/widgets/weekly_plan.py tests/test_weekly_plan.py
git commit -m "feat: 주간학습계획 질의 생성·파싱·그룹·기간 선택 순수 함수

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: WeeklyPlanWidget (GUI)

**Files:**
- Modify: `src/teacher_widgets/widgets/weekly_plan.py`
- Test: `tests/test_weekly_plan.py`

**Interfaces:**
- Consumes: Task 1 (`anon_sign_in`, `firestore_run_query`, `firestore_get_document`, `read_cache`, `write_cache`), Task 2 순수부, `BaseWidget`, `responsive`, `timetable.build_app_command`/웹앱 패턴.
- Produces:
  - `class PlanFetchWorker(QtCore.QThread)` — `__init__(settings)`, 시그널 `finished_ok(dict)`/`failed(str)`. run(): 인증 → `build_schedules_query(week_monday, week_monday+7)` runQuery(parent `artifacts/{aid}/public/data`) → messages GET(`.../weekly_messages/{monday}` — HTTPError 404는 빈 메시지로 무시) → `{"fetched_at", "week_monday", "entries", "messages"}` emit.
  - `class WeeklyPlanWidget(BaseWidget)` (widget_name="weekly_plan", BASE_SIZE=(320, 360))
    - `cache_path`, `apply_data(data)`, `render_plan()` (현재 tier로 일자 섹션 재구성), `refresh()`, `_on_fetch_ok/_on_fetch_failed`, `_shutdown_worker`, `showEvent/hideEvent`, `_custom_menu_actions`(새로고침), `mouseDoubleClickEvent`→`open_webapp()`(timetable의 `build_app_command` 재사용 + 자체 `_web_proc`), `current_tier() -> str` (`resolve_breakpoint(self.height(), PLAN_TIERS)`), `on_resized`(tier 변화 시에만 `render_plan`).
    - 속성: `header_label`, `status_label`, `days_container`(QVBoxLayout에 동적 라벨), `_data: dict|None`, `_tier: str`

- [ ] **Step 1: 실패하는 테스트 작성 (test_weekly_plan.py에 추가)**

```python
import json

from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.widgets.weekly_plan import WeeklyPlanWidget

PLAN_CACHE = {
    "fetched_at": "2026-07-02T10:00:00",
    "week_monday": "2026-06-29",
    "entries": [
        {"date": "2026-07-02", "department": "학사일정", "content": "기말평가주간", "order": 0},
        {"date": "2026-07-02", "department": "행정실", "content": "체육관 공사", "order": 1},
        {"date": "2026-07-03", "department": "5학년", "content": "진단검사", "order": 0},
    ],
    "messages": {"principal": "안전 제일", "vicePrincipal": ""},
}


def make_plan_widget(qtbot, tmp_path, cache=PLAN_CACHE):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    store.data["weekly_plan"]["_skip_initial_fetch"] = True
    if cache is not None:
        p = tmp_path / "cache" / "weekly_plan.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    w = WeeklyPlanWidget(store)
    qtbot.addWidget(w)
    return store, w


def test_plan_widget_renders_cache(qtbot, tmp_path):
    store, w = make_plan_widget(qtbot, tmp_path)
    assert w.widget_name == "weekly_plan"
    text = w.days_text()  # 렌더된 전체 텍스트 요약 접근자
    assert "기말평가주간" in text


def test_plan_widget_no_cache_empty_state(qtbot, tmp_path):
    store, w = make_plan_widget(qtbot, tmp_path, cache=None)
    assert "데이터 없음" in w.status_label.text() or "새로고침" in w.status_label.text()


def test_plan_widget_tier_from_height(qtbot, tmp_path):
    store, w = make_plan_widget(qtbot, tmp_path)
    w.resize(320, 200)
    assert w.current_tier() == "compact"
    w.resize(320, 350)
    assert w.current_tier() == "two_days"
    w.resize(320, 600)
    assert w.current_tier() == "week"


def test_plan_widget_hakssa_badge_precedes(qtbot, tmp_path):
    store, w = make_plan_widget(qtbot, tmp_path)
    w.resize(320, 600)
    w.render_plan()
    text = w.days_text()
    assert text.index("기말평가주간") < text.index("체육관 공사")
```

(`days_text()`는 렌더된 일자 섹션 라벨들의 텍스트를 이어붙여 반환하는 테스트 친화 접근자 — Widget에 구현.)

- [ ] **Step 2: RED 확인** — `.venv/Scripts/python.exe -m pytest tests/test_weekly_plan.py -k widget -v` → ImportError

- [ ] **Step 3: 구현 — weekly_plan.py에 추가**

import 보강:
```python
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from teacher_widgets.core.base_widget import BaseWidget
from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.core.data_remote import (
    anon_sign_in,
    firestore_get_document,
    firestore_run_query,
    read_cache,
    write_cache,
)
from teacher_widgets.core.responsive import resolve_breakpoint, scale_factor, scaled_font_pt
from teacher_widgets.widgets.timetable import build_app_command

import subprocess
import urllib.error
import webbrowser
```

클래스:
```python
class PlanFetchWorker(QtCore.QThread):
    finished_ok = QtCore.Signal(dict)
    failed = QtCore.Signal(str)

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self._settings = dict(settings)

    def run(self) -> None:
        try:
            s = self._settings
            token = anon_sign_in(s["api_key"])
            monday = week_monday(datetime.date.today())
            end = monday + datetime.timedelta(days=7)
            parent_path = f"artifacts/{s['artifact_app_id']}/public/data"
            docs = firestore_run_query(
                s["project_id"], parent_path,
                build_schedules_query(monday.isoformat(), end.isoformat()),
                token,
            )
            entries = parse_schedule_docs(docs)
            try:
                msg_doc = firestore_get_document(
                    s["project_id"],
                    f"{parent_path}/weekly_messages/{monday.isoformat()}",
                    token,
                )
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    msg_doc = None  # 이번 주 말씀 미작성 — 정상
                else:
                    raise
            data = {
                "fetched_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "week_monday": monday.isoformat(),
                "entries": entries,
                "messages": parse_messages_doc(msg_doc),
            }
            self.finished_ok.emit(data)
        except Exception as exc:
            self.failed.emit(str(exc))


class WeeklyPlanWidget(BaseWidget):
    BASE_SIZE = (320, 360)

    def __init__(self, store: ConfigStore):
        super().__init__("weekly_plan", store)
        self.cache_path = Path(store.path).parent / "cache" / "weekly_plan.json"
        self._data: dict | None = None
        self._worker: PlanFetchWorker | None = None
        self._web_proc = None
        self._tier = ""

        self.header_label = QtWidgets.QLabel("주간학습계획", alignment=QtCore.Qt.AlignCenter)
        self.header_label.setStyleSheet("font-weight:700; color:#2b2b2b;")
        self.status_label = QtWidgets.QLabel("", alignment=QtCore.Qt.AlignCenter)
        self.status_label.setStyleSheet("color:#999;")
        self.content_layout.addWidget(self.header_label)
        self.content_layout.addWidget(self.status_label)

        days_widget = QtWidgets.QWidget()
        self.days_layout = QtWidgets.QVBoxLayout(days_widget)
        self.days_layout.setContentsMargins(0, 0, 0, 0)
        self.days_layout.setSpacing(4)
        self.content_layout.addWidget(days_widget, stretch=1)

        cached = read_cache(self.cache_path)
        if cached is not None:
            self._data = cached
            self.status_label.setText(f"갱신: {cached.get('fetched_at', '')[:16]}")
        else:
            self.status_label.setText("데이터 없음 — 우클릭 → 새로고침")
        self.render_plan()

        self._refresh_timer = QtCore.QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh)

        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._shutdown_worker)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(QtGui.QColor(255, 255, 255, 235))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 16, 16)

    # --- 수명주기 (시간표 패턴) ---
    def showEvent(self, event) -> None:
        super().showEvent(event)
        minutes = int(self.store.data["weekly_plan"].get("refresh_minutes", 30))
        self._refresh_timer.start(minutes * 60 * 1000)
        if not self.store.data["weekly_plan"].get("_skip_initial_fetch", False):
            self.refresh()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._refresh_timer.stop()

    def _shutdown_worker(self) -> None:
        worker = self._worker
        if worker is not None and worker.isRunning():
            worker.wait(2000)

    # --- 데이터 ---
    def refresh(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        self._worker = PlanFetchWorker(self.store.data["weekly_plan"], self)
        self._worker.finished_ok.connect(self._on_fetch_ok)
        self._worker.failed.connect(self._on_fetch_failed)
        self._worker.start()

    def _on_fetch_ok(self, data: dict) -> None:
        self.apply_data(data)
        self.status_label.setText(f"갱신: {data.get('fetched_at', '')[:16]}")

    def _on_fetch_failed(self, msg: str) -> None:
        self.status_label.setText("갱신 실패 — 캐시 표시 중")
        self.setToolTip(msg)

    def apply_data(self, data: dict) -> None:
        self._data = data
        write_cache(self.cache_path, data)
        self.render_plan()

    # --- 렌더 ---
    def current_tier(self) -> str:
        return resolve_breakpoint(self.height(), PLAN_TIERS)

    def days_text(self) -> str:
        """테스트/디버그용: 렌더된 일자 섹션 텍스트를 이어붙여 반환."""
        parts = []
        for i in range(self.days_layout.count()):
            wdg = self.days_layout.itemAt(i).widget()
            if isinstance(wdg, QtWidgets.QLabel):
                parts.append(wdg.text())
        return "\n".join(parts)

    def render_plan(self) -> None:
        while self.days_layout.count():
            item = self.days_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._tier = self.current_tier()

        entries = (self._data or {}).get("entries", [])
        grouped = group_entries(entries)
        monday_iso = (self._data or {}).get("week_monday")
        today = datetime.date.today()
        monday = (datetime.date.fromisoformat(monday_iso)
                  if monday_iso else week_monday(today))
        weekday_names = ["월", "화", "수", "목", "금", "토", "일"]

        for day in pick_days(self._tier, monday, today):
            iso = day.isoformat()
            head = QtWidgets.QLabel(
                f"{day.month}/{day.day} ({weekday_names[day.weekday()]})"
                + ("  ← 오늘" if day == today else "")
            )
            head.setStyleSheet(
                "font-weight:600; color:#2b6e4f;" if day == today
                else "font-weight:600; color:#666;"
            )
            self.days_layout.addWidget(head)
            items = grouped.get(iso, [])
            if not items:
                empty = QtWidgets.QLabel("  일정 없음")
                empty.setStyleSheet("color:#bbb;")
                self.days_layout.addWidget(empty)
                continue
            for e in items:
                badge = "🟠" if e["department"] == "학사일정" else "▪"
                lbl = QtWidgets.QLabel(f"  {badge} [{e['department']}] {e['content']}")
                lbl.setWordWrap(True)
                lbl.setStyleSheet("color:#2b2b2b;")
                self.days_layout.addWidget(lbl)

        if self._tier == "week":
            messages = (self._data or {}).get("messages", {})
            for key, title in (("principal", "교장선생님"), ("vicePrincipal", "교감선생님")):
                text = (messages.get(key) or "").strip()
                if text:
                    lbl = QtWidgets.QLabel(f"💬 {title}: {text}")
                    lbl.setWordWrap(True)
                    lbl.setStyleSheet("color:#2b6e4f;")
                    self.days_layout.addWidget(lbl)
        self._apply_responsive()

    # --- 메뉴/웹앱 ---
    def _custom_menu_actions(self, menu) -> dict:
        refresh_action = menu.addAction("새로고침")
        return {refresh_action: self.refresh}

    def open_webapp(self) -> None:
        url = self.store.data["weekly_plan"].get("webapp_url", "")
        if not url:
            return
        if self._web_proc is not None and self._web_proc.poll() is None:
            return  # 이미 실행 중 (bring-to-front는 timetable 위젯과 달리 생략 — 단순화)
        cmd = build_app_command(url)
        if cmd:
            self._web_proc = subprocess.Popen(cmd)
        else:
            webbrowser.open(url)

    def mouseDoubleClickEvent(self, event) -> None:
        self.open_webapp()
        event.accept()

    # --- 반응형 ---
    def _apply_responsive(self) -> None:
        factor = scale_factor((self.width(), self.height()), self.BASE_SIZE)
        self.header_label.setStyleSheet(
            f"font-weight:700; color:#2b2b2b; font-size:{scaled_font_pt(12, factor)}pt;"
        )
        self.status_label.setStyleSheet(
            f"color:#999; font-size:{scaled_font_pt(8, factor)}pt;"
        )

    def on_resized(self, width: int, height: int) -> None:
        new_tier = self.current_tier()
        if new_tier != self._tier:
            self.render_plan()
        else:
            self._apply_responsive()
```

(참고: `datetime`은 순수부에서 이미 import됨.)

- [ ] **Step 4: GREEN + 전체 스위트**

Run: `.venv/Scripts/python.exe -m pytest -q` → 118 passed 예상 (114+4). 네트워크 없음 확인(빠른 실행 시간).

- [ ] **Step 5: 커밋**

```bash
git add src/teacher_widgets/widgets/weekly_plan.py tests/test_weekly_plan.py
git commit -m "feat: 주간학습계획 위젯(runQuery·내용구간·말씀·웹앱 실행)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: 급식 위젯 (meal)

**Files:**
- Create: `src/teacher_widgets/widgets/meal.py`
- Test: `tests/test_meal.py`

**Interfaces:**
- Consumes: Task 1 (`http_get_json`, `read_cache`, `write_cache`), BaseWidget, responsive.
- Produces:
  - `build_meal_url(edu_code, school_code, from_ymd, to_ymd, api_key="") -> str` (Type=json, KEY는 api_key 있을 때만)
  - `parse_meal_response(payload: dict) -> list[dict]` → `[{date:"YYYYMMDD", menu:[{name, allergy}], cal:"641.5 Kcal"}]`; INFO-200(데이터 없음)/형식 이상 → `[]`
  - `split_allergy(item: str) -> tuple[str, str]` — `"떡갈비 (2.4.5)"` → `("떡갈비", "2.4.5")`; 코드 없으면 `("깍두기*", "")` (이름 그대로, 공백 정리)
  - `MEAL_TIERS = [(0, "today"), (420, "week")]`
  - `class MealFetchWorker(QtCore.QThread)` — 이번 주 월~금 범위 1회 GET.
  - `class MealWidget(BaseWidget)` (widget_name="meal", BASE_SIZE=(240, 300)) — 시간표/주간계획과 동일 수명주기·캐시(`cache/meal.json`)·상태 라벨. `render_meal()`: today 구간=오늘 메뉴 리스트+칼로리(알레르기는 회색 첨자), week 구간=요일별 섹션. 오늘 데이터 없음 → "오늘은 급식 정보가 없습니다". `menu_text()` 테스트 접근자.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_meal.py`:
```python
import json

from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.widgets.meal import (
    build_meal_url,
    parse_meal_response,
    split_allergy,
    MEAL_TIERS,
    MealWidget,
)


def test_build_meal_url_without_key():
    url = build_meal_url("B10", "7031170", "20260629", "20260703")
    assert "mealServiceDietInfo" in url
    assert "ATPT_OFCDC_SC_CODE=B10" in url
    assert "SD_SCHUL_CODE=7031170" in url
    assert "MLSV_FROM_YMD=20260629" in url and "MLSV_TO_YMD=20260703" in url
    assert "KEY=" not in url


def test_build_meal_url_with_key():
    assert "KEY=abc123" in build_meal_url("B10", "7031170", "20260629", "20260703", "abc123")


def test_split_allergy():
    assert split_allergy("햄프씨드떡갈비 (2.4.5.6.10.12.15.16)") == ("햄프씨드떡갈비", "2.4.5.6.10.12.15.16")
    assert split_allergy("들기름김 ") == ("들기름김", "")
    assert split_allergy("깍두기* (9)") == ("깍두기*", "9")


SAMPLE = {"mealServiceDietInfo": [
    {"head": [{"list_total_count": 2}]},
    {"row": [
        {"MLSV_YMD": "20260702", "MMEAL_SC_NM": "중식",
         "DDISH_NM": "퀴노아찹쌀밥 <br/>햄프씨드떡갈비 (2.4.5)<br/>깍두기* (9)",
         "CAL_INFO": "641.5 Kcal"},
        {"MLSV_YMD": "20260703", "MMEAL_SC_NM": "중식",
         "DDISH_NM": "현미밥 <br/>미역국 (5)", "CAL_INFO": "600 Kcal"},
    ]},
]}

EMPTY = {"RESULT": {"CODE": "INFO-200", "MESSAGE": "해당하는 데이터가 없습니다."}}


def test_parse_meal_response():
    meals = parse_meal_response(SAMPLE)
    assert len(meals) == 2
    first = meals[0]
    assert first["date"] == "20260702"
    assert first["cal"] == "641.5 Kcal"
    assert first["menu"][0] == {"name": "퀴노아찹쌀밥", "allergy": ""}
    assert first["menu"][1] == {"name": "햄프씨드떡갈비", "allergy": "2.4.5"}


def test_parse_meal_response_empty_and_garbage():
    assert parse_meal_response(EMPTY) == []
    assert parse_meal_response({}) == []


def test_meal_tiers():
    assert MEAL_TIERS == [(0, "today"), (420, "week")]


MEAL_CACHE = {
    "fetched_at": "2026-07-02T07:00:00",
    "meals": [
        {"date": "20260702", "cal": "641.5 Kcal",
         "menu": [{"name": "퀴노아찹쌀밥", "allergy": ""},
                  {"name": "햄프씨드떡갈비", "allergy": "2.4.5"}]},
    ],
}


def make_meal_widget(qtbot, tmp_path, cache=MEAL_CACHE):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    store.data["meal"]["_skip_initial_fetch"] = True
    if cache is not None:
        p = tmp_path / "cache" / "meal.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    w = MealWidget(store)
    qtbot.addWidget(w)
    return store, w


def test_meal_widget_renders_today(qtbot, tmp_path, monkeypatch):
    import datetime as dt

    class FakeDate(dt.date):
        @classmethod
        def today(cls):
            return cls(2026, 7, 2)

    from teacher_widgets.widgets import meal as meal_mod
    monkeypatch.setattr(meal_mod.datetime, "date", FakeDate)
    store, w = make_meal_widget(qtbot, tmp_path)
    w.render_meal()
    text = w.menu_text()
    assert "퀴노아찹쌀밥" in text
    assert "641.5" in text


def test_meal_widget_no_data_message(qtbot, tmp_path):
    store, w = make_meal_widget(qtbot, tmp_path, cache={"fetched_at": "x", "meals": []})
    w.render_meal()
    assert "급식 정보가 없습니다" in w.menu_text()
```

- [ ] **Step 2: RED 확인** — ModuleNotFoundError

- [ ] **Step 3: 구현**

`src/teacher_widgets/widgets/meal.py`:
```python
"""급식 위젯: 나이스 개방 API(mealServiceDietInfo)."""

from __future__ import annotations

import datetime
import re
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from teacher_widgets.core.base_widget import BaseWidget
from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.core.data_remote import http_get_json, read_cache, write_cache
from teacher_widgets.core.responsive import resolve_breakpoint, scale_factor, scaled_font_pt

MEAL_TIERS = [(0, "today"), (420, "week")]

_ALLERGY_RE = re.compile(r"\s*\(([\d\.]+)\)\s*$")


def build_meal_url(edu_code: str, school_code: str, from_ymd: str,
                   to_ymd: str, api_key: str = "") -> str:
    url = ("https://open.neis.go.kr/hub/mealServiceDietInfo?Type=json"
           f"&ATPT_OFCDC_SC_CODE={edu_code}&SD_SCHUL_CODE={school_code}"
           f"&MLSV_FROM_YMD={from_ymd}&MLSV_TO_YMD={to_ymd}")
    if api_key:
        url += f"&KEY={api_key}"
    return url


def split_allergy(item: str) -> tuple[str, str]:
    item = item.strip()
    m = _ALLERGY_RE.search(item)
    if m:
        return item[: m.start()].strip(), m.group(1)
    return item, ""


def parse_meal_response(payload: dict) -> list[dict]:
    info = payload.get("mealServiceDietInfo")
    if not isinstance(info, list) or len(info) < 2:
        return []  # INFO-200(데이터 없음) 또는 형식 이상
    rows = info[1].get("row", [])
    meals = []
    for r in rows:
        menu = []
        for item in r.get("DDISH_NM", "").split("<br/>"):
            name, allergy = split_allergy(item)
            if name:
                menu.append({"name": name, "allergy": allergy})
        meals.append({
            "date": r.get("MLSV_YMD", ""),
            "cal": r.get("CAL_INFO", ""),
            "menu": menu,
        })
    return meals


class MealFetchWorker(QtCore.QThread):
    finished_ok = QtCore.Signal(dict)
    failed = QtCore.Signal(str)

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self._settings = dict(settings)

    def run(self) -> None:
        try:
            s = self._settings
            today = datetime.date.today()
            monday = today - datetime.timedelta(days=today.weekday())
            friday = monday + datetime.timedelta(days=4)
            url = build_meal_url(
                s["edu_code"], s["school_code"],
                monday.strftime("%Y%m%d"), friday.strftime("%Y%m%d"),
                s.get("api_key", ""),
            )
            meals = parse_meal_response(http_get_json(url))
            self.finished_ok.emit({
                "fetched_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "meals": meals,
            })
        except Exception as exc:
            self.failed.emit(str(exc))


class MealWidget(BaseWidget):
    BASE_SIZE = (240, 300)

    def __init__(self, store: ConfigStore):
        super().__init__("meal", store)
        self.cache_path = Path(store.path).parent / "cache" / "meal.json"
        self._data: dict | None = None
        self._worker: MealFetchWorker | None = None
        self._tier = ""

        self.header_label = QtWidgets.QLabel("🍽 오늘 급식", alignment=QtCore.Qt.AlignCenter)
        self.header_label.setStyleSheet("font-weight:700; color:#2b2b2b;")
        self.status_label = QtWidgets.QLabel("", alignment=QtCore.Qt.AlignCenter)
        self.status_label.setStyleSheet("color:#999;")
        self.content_layout.addWidget(self.header_label)
        self.content_layout.addWidget(self.status_label)

        body = QtWidgets.QWidget()
        self.body_layout = QtWidgets.QVBoxLayout(body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(2)
        self.content_layout.addWidget(body, stretch=1)

        cached = read_cache(self.cache_path)
        if cached is not None:
            self._data = cached
            self.status_label.setText(f"갱신: {cached.get('fetched_at', '')[:16]}")
        else:
            self.status_label.setText("데이터 없음 — 우클릭 → 새로고침")
        self.render_meal()

        self._refresh_timer = QtCore.QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh)
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._shutdown_worker)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(QtGui.QColor(255, 255, 255, 235))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 16, 16)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        minutes = int(self.store.data["meal"].get("refresh_minutes", 360))
        self._refresh_timer.start(minutes * 60 * 1000)
        if not self.store.data["meal"].get("_skip_initial_fetch", False):
            self.refresh()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._refresh_timer.stop()

    def _shutdown_worker(self) -> None:
        worker = self._worker
        if worker is not None and worker.isRunning():
            worker.wait(2000)

    def refresh(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        self._worker = MealFetchWorker(self.store.data["meal"], self)
        self._worker.finished_ok.connect(self._on_fetch_ok)
        self._worker.failed.connect(self._on_fetch_failed)
        self._worker.start()

    def _on_fetch_ok(self, data: dict) -> None:
        self._data = data
        write_cache(self.cache_path, data)
        self.status_label.setText(f"갱신: {data.get('fetched_at', '')[:16]}")
        self.render_meal()

    def _on_fetch_failed(self, msg: str) -> None:
        self.status_label.setText("갱신 실패 — 캐시 표시 중")
        self.setToolTip(msg)

    # --- 렌더 ---
    def current_tier(self) -> str:
        return resolve_breakpoint(self.height(), MEAL_TIERS)

    def menu_text(self) -> str:
        parts = []
        for i in range(self.body_layout.count()):
            wdg = self.body_layout.itemAt(i).widget()
            if isinstance(wdg, QtWidgets.QLabel):
                parts.append(wdg.text())
        return "\n".join(parts)

    def _add_menu_lines(self, meal: dict, compact: bool) -> None:
        for m in meal["menu"]:
            suffix = f"  ({m['allergy']})" if m["allergy"] else ""
            lbl = QtWidgets.QLabel(f"· {m['name']}{suffix}")
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color:#2b2b2b;")
            self.body_layout.addWidget(lbl)
            if compact and self.body_layout.count() > 12:
                break
        if meal.get("cal"):
            cal = QtWidgets.QLabel(meal["cal"])
            cal.setStyleSheet("color:#999;")
            self.body_layout.addWidget(cal)

    def render_meal(self) -> None:
        while self.body_layout.count():
            item = self.body_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._tier = self.current_tier()
        meals = (self._data or {}).get("meals", [])
        today_ymd = datetime.date.today().strftime("%Y%m%d")
        weekday_names = ["월", "화", "수", "목", "금", "토", "일"]

        if self._tier == "today":
            todays = [m for m in meals if m["date"] == today_ymd]
            if not todays:
                lbl = QtWidgets.QLabel("오늘은 급식 정보가 없습니다")
                lbl.setStyleSheet("color:#bbb;")
                self.body_layout.addWidget(lbl)
            else:
                self._add_menu_lines(todays[0], compact=True)
        else:
            shown = False
            for m in meals:
                try:
                    d = datetime.datetime.strptime(m["date"], "%Y%m%d").date()
                except ValueError:
                    continue
                head = QtWidgets.QLabel(
                    f"{d.month}/{d.day} ({weekday_names[d.weekday()]})"
                    + ("  ← 오늘" if m["date"] == today_ymd else "")
                )
                head.setStyleSheet("font-weight:600; color:#666;")
                self.body_layout.addWidget(head)
                self._add_menu_lines(m, compact=True)
                shown = True
            if not shown:
                lbl = QtWidgets.QLabel("이번 주 급식 정보가 없습니다")
                lbl.setStyleSheet("color:#bbb;")
                self.body_layout.addWidget(lbl)
        self._apply_responsive()

    def _custom_menu_actions(self, menu) -> dict:
        refresh_action = menu.addAction("새로고침")
        return {refresh_action: self.refresh}

    def _apply_responsive(self) -> None:
        factor = scale_factor((self.width(), self.height()), self.BASE_SIZE)
        self.header_label.setStyleSheet(
            f"font-weight:700; color:#2b2b2b; font-size:{scaled_font_pt(12, factor)}pt;"
        )
        self.status_label.setStyleSheet(
            f"color:#999; font-size:{scaled_font_pt(8, factor)}pt;"
        )

    def on_resized(self, width: int, height: int) -> None:
        new_tier = self.current_tier()
        if new_tier != self._tier:
            self.render_meal()
        else:
            self._apply_responsive()
```

- [ ] **Step 4: GREEN + 전체 스위트** — 126 passed 예상 (118+8).

- [ ] **Step 5: 커밋**

```bash
git add src/teacher_widgets/widgets/meal.py tests/test_meal.py
git commit -m "feat: 급식 위젯(나이스 API·알레르기 파싱·오늘/주간 구간)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: 날씨 위젯 (weather)

**Files:**
- Create: `src/teacher_widgets/widgets/weather.py`
- Test: `tests/test_weather.py`

**Interfaces:**
- Consumes: Task 1 (`http_get_json`, `read_cache`, `write_cache`), BaseWidget, responsive.
- Produces:
  - `build_forecast_url(lat, lon) -> str` / `build_air_url(lat, lon) -> str`
  - `wmo_to_text(code: int) -> str` — `"맑음 ☀️"` 등 (0맑음/1·2구름조금/3흐림/45·48안개/51~57이슬비/61~67비/71~77눈/80~82소나기/85·86소낙눈/95~99뇌우, 그 외 `"-"`)
  - `pm10_grade(v) -> str` / `pm25_grade(v) -> str` — 좋음/보통/나쁨/매우나쁨 (Global Constraints 기준), None → `"-"`
  - `parse_weather(forecast: dict, air: dict) -> dict` → `{"temp": float|None, "code": int|None, "today_max","today_min","tomorrow_max","tomorrow_min","tomorrow_rain","pm10","pm25"}` (누락 필드는 None)
  - `WEATHER_TIERS = [(0, "now"), (300, "two_days")]`
  - `class WeatherFetchWorker(QtCore.QThread)` — forecast/air 2회 GET; **하나 실패해도 성공분 반영**(둘 다 실패 시에만 failed).
  - `class WeatherWidget(BaseWidget)` (widget_name="weather", BASE_SIZE=(220, 240)) — 동일 수명주기·캐시(`cache/weather.json`). 렌더: 현재기온(큰 글씨)+상태, 오늘 최고/최저, PM 배지; two_days 구간에 내일 줄. `body_text()` 테스트 접근자.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_weather.py`:
```python
import json

from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.widgets.weather import (
    build_forecast_url,
    build_air_url,
    wmo_to_text,
    pm10_grade,
    pm25_grade,
    parse_weather,
    WEATHER_TIERS,
    WeatherWidget,
)


def test_urls_contain_coords_and_fields():
    f = build_forecast_url(37.617, 126.921)
    assert "latitude=37.617" in f and "longitude=126.921" in f
    assert "temperature_2m_max" in f and "forecast_days=2" in f
    a = build_air_url(37.617, 126.921)
    assert "air-quality" in a and "pm2_5" in a


def test_wmo_mapping():
    assert "맑음" in wmo_to_text(0)
    assert "흐림" in wmo_to_text(3)
    assert "비" in wmo_to_text(63)
    assert "눈" in wmo_to_text(73)
    assert "뇌우" in wmo_to_text(95)
    assert wmo_to_text(42) == "-"


def test_pm_grades():
    assert pm10_grade(25) == "좋음"
    assert pm10_grade(50) == "보통"
    assert pm10_grade(100) == "나쁨"
    assert pm10_grade(200) == "매우나쁨"
    assert pm25_grade(10) == "좋음"
    assert pm25_grade(36) == "나쁨"
    assert pm10_grade(None) == "-"


FORECAST = {
    "current": {"temperature_2m": 26.0, "weather_code": 1},
    "daily": {
        "temperature_2m_max": [26.2, 27.2],
        "temperature_2m_min": [19.6, 20.2],
        "precipitation_probability_max": [10, 74],
        "weather_code": [1, 61],
    },
}
AIR = {"current": {"pm10": 22.8, "pm2_5": 19.4}}


def test_parse_weather():
    out = parse_weather(FORECAST, AIR)
    assert out["temp"] == 26.0 and out["code"] == 1
    assert out["today_max"] == 26.2 and out["tomorrow_min"] == 20.2
    assert out["tomorrow_rain"] == 74
    assert out["pm10"] == 22.8 and out["pm25"] == 19.4


def test_parse_weather_partial():
    out = parse_weather({}, AIR)
    assert out["temp"] is None and out["pm10"] == 22.8
    out2 = parse_weather(FORECAST, {})
    assert out2["pm10"] is None and out2["temp"] == 26.0


def test_weather_tiers():
    assert WEATHER_TIERS == [(0, "now"), (300, "two_days")]


WEATHER_CACHE = {
    "fetched_at": "2026-07-02T10:00:00",
    "weather": {"temp": 26.0, "code": 1, "today_max": 26.2, "today_min": 19.6,
                "tomorrow_max": 27.2, "tomorrow_min": 20.2, "tomorrow_rain": 74,
                "pm10": 22.8, "pm25": 19.4},
}


def make_weather_widget(qtbot, tmp_path, cache=WEATHER_CACHE):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    store.data["weather"]["_skip_initial_fetch"] = True
    if cache is not None:
        p = tmp_path / "cache" / "weather.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    w = WeatherWidget(store)
    qtbot.addWidget(w)
    return store, w


def test_weather_widget_renders_cache(qtbot, tmp_path):
    store, w = make_weather_widget(qtbot, tmp_path)
    text = w.body_text()
    assert "26.0" in text or "26" in text
    assert "좋음" in text or "보통" in text  # PM 배지


def test_weather_widget_two_days_tier(qtbot, tmp_path):
    store, w = make_weather_widget(qtbot, tmp_path)
    w.resize(220, 350)
    w.render_weather()
    assert "내일" in w.body_text()
```

- [ ] **Step 2: RED 확인** — ModuleNotFoundError

- [ ] **Step 3: 구현**

`src/teacher_widgets/widgets/weather.py`:
```python
"""날씨 위젯: Open-Meteo forecast + air-quality (키 불필요)."""

from __future__ import annotations

import datetime
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from teacher_widgets.core.base_widget import BaseWidget
from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.core.data_remote import http_get_json, read_cache, write_cache
from teacher_widgets.core.responsive import resolve_breakpoint, scale_factor, scaled_font_pt

WEATHER_TIERS = [(0, "now"), (300, "two_days")]

_WMO = [
    ((0, 0), "맑음 ☀️"),
    ((1, 2), "구름 조금 🌤️"),
    ((3, 3), "흐림 ☁️"),
    ((45, 48), "안개 🌫️"),
    ((51, 57), "이슬비 🌦️"),
    ((61, 67), "비 🌧️"),
    ((71, 77), "눈 🌨️"),
    ((80, 82), "소나기 🌧️"),
    ((85, 86), "소낙눈 🌨️"),
    ((95, 99), "뇌우 ⛈️"),
]


def build_forecast_url(lat: float, lon: float) -> str:
    return ("https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            "&current=temperature_2m,weather_code"
            "&daily=weather_code,temperature_2m_max,temperature_2m_min,"
            "precipitation_probability_max"
            "&timezone=Asia%2FSeoul&forecast_days=2")


def build_air_url(lat: float, lon: float) -> str:
    return ("https://air-quality-api.open-meteo.com/v1/air-quality"
            f"?latitude={lat}&longitude={lon}"
            "&current=pm10,pm2_5&timezone=Asia%2FSeoul")


def wmo_to_text(code: int) -> str:
    for (lo, hi), text in _WMO:
        if lo <= code <= hi:
            return text
    return "-"


def _grade(value, bounds: tuple[int, int, int]) -> str:
    if value is None:
        return "-"
    good, normal, bad = bounds
    if value <= good:
        return "좋음"
    if value <= normal:
        return "보통"
    if value <= bad:
        return "나쁨"
    return "매우나쁨"


def pm10_grade(value) -> str:
    return _grade(value, (30, 80, 150))


def pm25_grade(value) -> str:
    return _grade(value, (15, 35, 75))


def _daily(forecast: dict, key: str, idx: int):
    values = forecast.get("daily", {}).get(key, [])
    return values[idx] if len(values) > idx else None


def parse_weather(forecast: dict, air: dict) -> dict:
    current = forecast.get("current", {})
    air_now = air.get("current", {})
    return {
        "temp": current.get("temperature_2m"),
        "code": current.get("weather_code"),
        "today_max": _daily(forecast, "temperature_2m_max", 0),
        "today_min": _daily(forecast, "temperature_2m_min", 0),
        "tomorrow_max": _daily(forecast, "temperature_2m_max", 1),
        "tomorrow_min": _daily(forecast, "temperature_2m_min", 1),
        "tomorrow_rain": _daily(forecast, "precipitation_probability_max", 1),
        "pm10": air_now.get("pm10"),
        "pm25": air_now.get("pm2_5"),
    }


class WeatherFetchWorker(QtCore.QThread):
    finished_ok = QtCore.Signal(dict)
    failed = QtCore.Signal(str)

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self._settings = dict(settings)

    def run(self) -> None:
        lat = self._settings.get("lat", 37.617)
        lon = self._settings.get("lon", 126.921)
        forecast, air = {}, {}
        errors = []
        try:
            forecast = http_get_json(build_forecast_url(lat, lon))
        except Exception as exc:
            errors.append(f"forecast: {exc}")
        try:
            air = http_get_json(build_air_url(lat, lon))
        except Exception as exc:
            errors.append(f"air: {exc}")
        if not forecast and not air:
            self.failed.emit("; ".join(errors))
            return
        self.finished_ok.emit({
            "fetched_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "weather": parse_weather(forecast, air),
        })


class WeatherWidget(BaseWidget):
    BASE_SIZE = (220, 240)

    def __init__(self, store: ConfigStore):
        super().__init__("weather", store)
        self.cache_path = Path(store.path).parent / "cache" / "weather.json"
        self._data: dict | None = None
        self._worker: WeatherFetchWorker | None = None
        self._tier = ""

        self.header_label = QtWidgets.QLabel("🌈 날씨", alignment=QtCore.Qt.AlignCenter)
        self.header_label.setStyleSheet("font-weight:700; color:#2b2b2b;")
        self.status_label = QtWidgets.QLabel("", alignment=QtCore.Qt.AlignCenter)
        self.status_label.setStyleSheet("color:#999;")
        self.content_layout.addWidget(self.header_label)
        self.content_layout.addWidget(self.status_label)

        body = QtWidgets.QWidget()
        self.body_layout = QtWidgets.QVBoxLayout(body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(2)
        self.content_layout.addWidget(body, stretch=1)

        cached = read_cache(self.cache_path)
        if cached is not None:
            self._data = cached
            self.status_label.setText(f"갱신: {cached.get('fetched_at', '')[:16]}")
        else:
            self.status_label.setText("데이터 없음 — 우클릭 → 새로고침")
        self.render_weather()

        self._refresh_timer = QtCore.QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh)
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._shutdown_worker)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(QtGui.QColor(255, 255, 255, 235))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 16, 16)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        minutes = int(self.store.data["weather"].get("refresh_minutes", 30))
        self._refresh_timer.start(minutes * 60 * 1000)
        if not self.store.data["weather"].get("_skip_initial_fetch", False):
            self.refresh()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._refresh_timer.stop()

    def _shutdown_worker(self) -> None:
        worker = self._worker
        if worker is not None and worker.isRunning():
            worker.wait(2000)

    def refresh(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        self._worker = WeatherFetchWorker(self.store.data["weather"], self)
        self._worker.finished_ok.connect(self._on_fetch_ok)
        self._worker.failed.connect(self._on_fetch_failed)
        self._worker.start()

    def _on_fetch_ok(self, data: dict) -> None:
        self._data = data
        write_cache(self.cache_path, data)
        self.status_label.setText(f"갱신: {data.get('fetched_at', '')[:16]}")
        self.render_weather()

    def _on_fetch_failed(self, msg: str) -> None:
        self.status_label.setText("갱신 실패 — 캐시 표시 중")
        self.setToolTip(msg)

    # --- 렌더 ---
    def current_tier(self) -> str:
        return resolve_breakpoint(self.height(), WEATHER_TIERS)

    def body_text(self) -> str:
        parts = []
        for i in range(self.body_layout.count()):
            wdg = self.body_layout.itemAt(i).widget()
            if isinstance(wdg, QtWidgets.QLabel):
                parts.append(wdg.text())
        return "\n".join(parts)

    def render_weather(self) -> None:
        while self.body_layout.count():
            item = self.body_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._tier = self.current_tier()
        wx = (self._data or {}).get("weather", {})

        temp = wx.get("temp")
        code = wx.get("code")
        big = QtWidgets.QLabel(
            (f"{temp}°C" if temp is not None else "-")
            + ("  " + wmo_to_text(int(code)) if code is not None else "")
        )
        big.setAlignment(QtCore.Qt.AlignCenter)
        big.setStyleSheet("font-size:20pt; font-weight:700; color:#2b2b2b;")
        self.body_layout.addWidget(big)

        tmax, tmin = wx.get("today_max"), wx.get("today_min")
        hilo = QtWidgets.QLabel(
            f"오늘 {tmax if tmax is not None else '-'}° / {tmin if tmin is not None else '-'}°"
        )
        hilo.setAlignment(QtCore.Qt.AlignCenter)
        hilo.setStyleSheet("color:#666;")
        self.body_layout.addWidget(hilo)

        pm = QtWidgets.QLabel(
            f"미세 {pm10_grade(wx.get('pm10'))} · 초미세 {pm25_grade(wx.get('pm25'))}"
        )
        pm.setAlignment(QtCore.Qt.AlignCenter)
        pm.setStyleSheet("color:#2b6e4f;")
        self.body_layout.addWidget(pm)

        if self._tier == "two_days":
            rain = wx.get("tomorrow_rain")
            tomorrow = QtWidgets.QLabel(
                f"내일 {wx.get('tomorrow_max', '-')}° / {wx.get('tomorrow_min', '-')}°"
                + (f" · 강수 {rain}%" if rain is not None else "")
            )
            tomorrow.setAlignment(QtCore.Qt.AlignCenter)
            tomorrow.setStyleSheet("color:#666;")
            self.body_layout.addWidget(tomorrow)
        self._apply_responsive()

    def _custom_menu_actions(self, menu) -> dict:
        refresh_action = menu.addAction("새로고침")
        return {refresh_action: self.refresh}

    def _apply_responsive(self) -> None:
        factor = scale_factor((self.width(), self.height()), self.BASE_SIZE)
        self.header_label.setStyleSheet(
            f"font-weight:700; color:#2b2b2b; font-size:{scaled_font_pt(11, factor)}pt;"
        )
        self.status_label.setStyleSheet(
            f"color:#999; font-size:{scaled_font_pt(8, factor)}pt;"
        )

    def on_resized(self, width: int, height: int) -> None:
        new_tier = self.current_tier()
        if new_tier != self._tier:
            self.render_weather()
        else:
            self._apply_responsive()
```

- [ ] **Step 4: GREEN + 전체 스위트** — 135 passed 예상 (126+9).

- [ ] **Step 5: 커밋**

```bash
git add src/teacher_widgets/widgets/weather.py tests/test_weather.py
git commit -m "feat: 날씨 위젯(Open-Meteo·WMO 매핑·미세먼지 등급)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: 런처 등록 + 실측 스모크 3종

**Files:**
- Modify: `src/teacher_widgets/main.py`
- Test: `tests/test_tray.py` (등록 확인 1개)

**Interfaces:**
- Consumes: Task 3~5 위젯 3종.
- Produces: main.py 등록 3줄. 실측 스모크(주간계획·급식·날씨) 결과.

- [ ] **Step 1: 테스트 작성 (test_tray.py에 추가 — 즉시 통과 예상)**

```python
def test_tray_menu_lists_phase3_widgets(qtbot, tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    reg = WidgetRegistry(store)
    for nm in ("weekly_plan", "meal", "weather"):
        reg.register(nm, lambda nm=nm: BaseWidget(nm, store))
    menu = build_tray_menu(reg)
    texts = [a.text() for a in menu.actions() if a.text()]
    for nm in ("weekly_plan", "meal", "weather"):
        assert nm in texts
```

- [ ] **Step 2: main.py 등록**

import 추가:
```python
from .widgets.weekly_plan import WeeklyPlanWidget
from .widgets.meal import MealWidget
from .widgets.weather import WeatherWidget
```
timetable 등록 다음에:
```python
    registry.register("weekly_plan", lambda: WeeklyPlanWidget(store))
    registry.register("meal", lambda: MealWidget(store))
    registry.register("weather", lambda: WeatherWidget(store))
```

- [ ] **Step 3: 전체 스위트** — 136 passed 예상.

- [ ] **Step 4: 실측 스모크 3종 (offscreen, 실 API 각 1회)**

Run:
```bash
QT_QPA_PLATFORM=offscreen PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "
import sys, tempfile, os; sys.path.insert(0, 'src')
from PySide6 import QtWidgets, QtCore
app = QtWidgets.QApplication([])
from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.widgets.weekly_plan import WeeklyPlanWidget
from teacher_widgets.widgets.meal import MealWidget
from teacher_widgets.widgets.weather import WeatherWidget
d = tempfile.mkdtemp(); s = ConfigStore(os.path.join(d, 'c.json')); s.load()
widgets = [WeeklyPlanWidget(s), MealWidget(s), WeatherWidget(s)]
for w in widgets: w.show()
def check():
    for w in widgets:
        name = w.widget_name
        print(name, '|', w.status_label.text(), '| tooltip:', repr(w.toolTip()[:60]))
    app.quit()
QtCore.QTimer.singleShot(12000, check)
app.exec()
"
```
Expected: 세 위젯 모두 `갱신: 2026-...` 상태. (주간계획이 429면 할당량 소진 — 보고에 명시하고 시간 경과 후 재시도 1회)

- [ ] **Step 5: 커밋**

```bash
git add src/teacher_widgets/main.py tests/test_tray.py
git commit -m "feat: 런처에 주간계획·급식·날씨 위젯 등록

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 자기 점검 (Self-Review)

**1. Spec 커버리지**
- SSL strict 완화 공용 컨텍스트 → Task 1 ✅ / runQuery·공용 GET → Task 1 ✅
- 주간계획: 월요일 계산(주말 규칙)·범위 질의·학사일정 우선 정렬·말씀(404 허용)·breakpoint 3단·웹앱 더블클릭 → Task 2~3 ✅
- 급식: 키 없는 URL(선택 키)·`<br/>`/알레르기 파싱·INFO-200 빈 처리·오늘/주간 2단·주간 1회 요청 → Task 4 ✅
- 날씨: Open-Meteo 2요청·부분 실패 허용·WMO 한글 매핑·PM 4등급·now/two_days 2단 → Task 5 ✅
- 공통 수명주기(showEvent/hideEvent/aboutToQuit/캐시/툴팁/`_skip_initial_fetch`) → Task 3·4·5 각 위젯 ✅
- config 기본값 3종 → Task 1 ✅ / 등록·실측 스모크 → Task 6 ✅
- 429 → 일반 실패 처리(캐시 유지) ✅ (별도 분기 불필요 — 스모크에서 확인)

**2. 플레이스홀더 스캔:** 없음 — 전 코드 스텝 실코드 ✅

**3. 타입 일관성:** `parse_schedule_docs->list[dict]`, `group_entries->dict`, `pick_days(tier,mon,today)->list[date]`, `parse_meal_response->list[dict]`, `split_allergy->(str,str)`, `parse_weather->dict`, 각 Worker `finished_ok(dict)/failed(str)`, 각 Widget `(store)` 생성자, 접근자 `days_text/menu_text/body_text` — Task 간 일치 ✅

**범위 밖:** edu-plan 백업 최적화, 기상청 실측 전환, 급식 조·석식.
