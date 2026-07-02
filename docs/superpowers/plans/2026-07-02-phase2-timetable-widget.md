# Phase 2 시간표 위젯 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Firestore(익명 인증)에서 학교 시간표를 읽어 학급/특별실/전담 뷰로 표시하고, 더블클릭 시 웹앱을 앱 모드 창으로 여는 읽기 전용 시간표 위젯을 만든다.

**Architecture:** 네트워크(익명 인증 + Firestore REST + 캐시)는 stdlib(urllib)만 쓰는 `core/data_remote.py`로 분리한다. Firestore JSON 파싱·뷰 필터·셀 병합·대상 목록 유도는 순수 함수로 만들어 픽스처 JSON으로 테스트한다. GUI는 `FetchWorker(QThread)`가 백그라운드에서 받아 시그널로 전달하고, `TimetableWidget(BaseWidget)`이 5×7 그리드로 렌더한다.

**Tech Stack:** Python 3.14, PySide6, urllib(의존성 추가 없음), pytest + pytest-qt.

## Global Constraints

- Python 3.14.x. PySide6 Widgets, QML 금지. 새 pip 의존성 추가 금지(urllib 등 stdlib만).
- 테스트는 `QT_QPA_PLATFORM=offscreen` 헤드리스 통과. 실행: `.venv/Scripts/python.exe -m pytest -v` (경로에 공백·한글 → 항상 따옴표).
- 테스트에서 실제 네트워크 호출 금지 — HTTP 함수는 얇게 유지하고 파싱·캐시만 테스트.
- Firestore 실측값(설정 기본값): apiKey `AIzaSyBLatEhyjsQDPNJVO5FWQHPfkdyaTQhrR0`, projectId `sunil-time-table`, artifact appId `seonil-timetable-v1`, 웹앱 URL `https://sunil-timetable.vercel.app/`.
- 문서 경로: `artifacts/{artifact_app_id}/public/data/timetables_state/global_state`.
- lesson 필드: `name·teacher·room·classId·day('월'~'금')·period(1~7 int)`. 캐시 형식: `{"fetched_at", "table_name", "lessons":[...]}`.
- 캐시 파일: config.json과 같은 폴더의 `cache/timetable.json` (config.json에 데이터 저장 금지).
- 위젯 식별자 `timetable`. config 슬롯 `timetable`(아래 Task 1에서 기본값 정의).
- BaseWidget 공개 멤버: `__init__(widget_name, store)`, `content_layout`, `BASE_SIZE`, `on_resized(w,h)`, `_custom_menu_actions(menu)->dict` 훅.
- 커밋 footer: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- 기존 72개 테스트를 깨뜨리지 말 것.

---

## 파일 구조

```
src/teacher_widgets/
├─ core/
│  ├─ data_remote.py       # (신규) 익명 인증·Firestore GET·캐시 read/write
│  └─ config_store.py      # (수정) DEFAULT_CONFIG에 timetable 기본값
├─ widgets/
│  └─ timetable.py         # (신규) 순수 파싱/필터 + TargetDialog + FetchWorker + TimetableWidget
└─ main.py                 # (수정) timetable 등록
tests/
├─ test_data_remote.py     # (신규) 캐시 라운드트립
├─ test_timetable.py       # (신규) 파싱·필터·셀·대상유도·다이얼로그·위젯
└─ test_tray.py            # (수정 없음 — tray는 일반적)
```

---

## Task 1: 원격 데이터 토대 (data_remote) + config 기본값

**Files:**
- Create: `src/teacher_widgets/core/data_remote.py`
- Modify: `src/teacher_widgets/core/config_store.py` (DEFAULT_CONFIG에 `timetable` 키)
- Test: `tests/test_data_remote.py`, `tests/test_config_store.py` (1개 추가)

**Interfaces:**
- Consumes: (없음)
- Produces:
  - `anon_sign_in(api_key: str, timeout: int = 15) -> str` (idToken; HTTP — 테스트 제외)
  - `firestore_get_document(project_id: str, doc_path: str, id_token: str, timeout: int = 30) -> dict` (HTTP — 테스트 제외)
  - `read_cache(path: Path) -> dict | None`
  - `write_cache(path: Path, data: dict) -> None` (부모 폴더 자동 생성, UTF-8)
  - `DEFAULT_CONFIG["timetable"]` = `{"api_key": ..., "project_id": ..., "artifact_app_id": ..., "webapp_url": ..., "view_type": "class", "target": "1-진", "refresh_minutes": 60}`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_data_remote.py`:
```python
from teacher_widgets.core.data_remote import read_cache, write_cache


def test_cache_roundtrip(tmp_path):
    path = tmp_path / "cache" / "timetable.json"  # 부모 폴더 없음 → 자동 생성 확인
    data = {
        "fetched_at": "2026-07-02T10:00:00",
        "table_name": "2026 기본 시간표",
        "lessons": [
            {"name": "국어", "teacher": "담임", "room": "교실",
             "classId": "1-진", "day": "월", "period": 1}
        ],
    }
    write_cache(path, data)
    assert read_cache(path) == data


def test_read_cache_missing_returns_none(tmp_path):
    assert read_cache(tmp_path / "nope.json") is None


def test_read_cache_corrupt_returns_none(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    assert read_cache(path) is None
```

`tests/test_config_store.py` 끝에 추가:
```python
def test_default_timetable_settings(tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    tt = store.data["timetable"]
    assert tt["view_type"] == "class"
    assert tt["target"] == "1-진"
    assert tt["project_id"] == "sunil-time-table"
    assert tt["refresh_minutes"] == 60
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `.venv/Scripts/python.exe -m pytest tests/test_data_remote.py tests/test_config_store.py -v`
Expected: FAIL (ModuleNotFoundError: data_remote / KeyError: 'timetable')

- [ ] **Step 3: 구현**

`src/teacher_widgets/core/data_remote.py`:
```python
"""외부 데이터 공용 토대: Firebase 익명 인증 · Firestore REST GET · 로컬 캐시.

stdlib(urllib)만 사용한다 — 배포본에 의존성을 추가하지 않기 위함.
HTTP 함수는 얇게 유지하고 테스트하지 않는다(파싱·캐시는 순수 함수로 테스트).
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path


def anon_sign_in(api_key: str, timeout: int = 15) -> str:
    """Firebase Identity Toolkit 익명 로그인 → idToken 반환."""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={api_key}"
    req = urllib.request.Request(
        url,
        data=json.dumps({"returnSecureToken": True}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)["idToken"]


def firestore_get_document(
    project_id: str, doc_path: str, id_token: str, timeout: int = 30
) -> dict:
    """Firestore REST로 문서 1개 GET (Firestore JSON 형식 그대로 반환)."""
    url = (
        f"https://firestore.googleapis.com/v1/projects/{project_id}"
        f"/databases/(default)/documents/{doc_path}"
    )
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {id_token}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def read_cache(path: Path) -> dict | None:
    """캐시 JSON 로드. 없거나 손상 시 None."""
    path = Path(path)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def write_cache(path: Path, data: dict) -> None:
    """캐시 JSON 저장. 부모 폴더 자동 생성."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
```

`config_store.py`의 `DEFAULT_CONFIG`에 키 추가 (`class_roster` 아래):
```python
    "timetable": {
        "api_key": "AIzaSyBLatEhyjsQDPNJVO5FWQHPfkdyaTQhrR0",
        "project_id": "sunil-time-table",
        "artifact_app_id": "seonil-timetable-v1",
        "webapp_url": "https://sunil-timetable.vercel.app/",
        "view_type": "class",
        "target": "1-진",
        "refresh_minutes": 60,
    },
```

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `.venv/Scripts/python.exe -m pytest tests/test_data_remote.py tests/test_config_store.py -v`
Expected: 신규 4개 포함 전부 통과.

- [ ] **Step 5: 전체 스위트 + 커밋**

Run: `.venv/Scripts/python.exe -m pytest -q` → 76 passed 예상.
```bash
git add src/teacher_widgets/core/data_remote.py src/teacher_widgets/core/config_store.py tests/test_data_remote.py tests/test_config_store.py
git commit -m "feat: 원격 데이터 토대(익명인증·Firestore GET·캐시)와 시간표 설정 기본값

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: 시간표 파싱·필터 순수 함수

**Files:**
- Create: `src/teacher_widgets/widgets/timetable.py` (순수 함수부만)
- Test: `tests/test_timetable.py`

**Interfaces:**
- Consumes: (없음 — 순수)
- Produces:
  - `DAYS = ["월", "화", "수", "목", "금"]`, `PERIODS = [1, 2, 3, 4, 5, 6, 7]`
  - `parse_global_state(fs_doc: dict) -> dict` → `{"table_name": str, "lessons": [{"name","teacher","room","classId","day","period"}...]}` (activeTableId 우선, 없으면 첫 시간표, 그것도 없으면 빈 결과)
  - `filter_lessons(lessons: list, view_type: str, target: str) -> dict[tuple[str, int], list]` (키=(day, period))
  - `cell_text(entries: list, view_type: str) -> str` (빈 리스트→"", class 뷰: room≠'교실'이면 `📍room` 병기, room/teacher 뷰: classId 표시, 3개 초과 `외 N`)
  - `derive_targets(lessons: list) -> dict` → `{"class": [...], "room": [...], "teacher": [...]}` (정렬, 빈 문자열 제외)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_timetable.py`:
```python
from teacher_widgets.widgets.timetable import (
    parse_global_state,
    filter_lessons,
    cell_text,
    derive_targets,
    DAYS,
    PERIODS,
)


def _fs_lesson(name, teacher, room, class_id, day, period):
    return {"mapValue": {"fields": {
        "name": {"stringValue": name},
        "teacher": {"stringValue": teacher},
        "room": {"stringValue": room},
        "classId": {"stringValue": class_id},
        "day": {"stringValue": day},
        "period": {"integerValue": str(period)},
        "color": {"stringValue": "bg-red-100"},
    }}}


def _fs_doc(active_id, tables):
    return {"fields": {
        "activeTableId": {"stringValue": active_id},
        "updatedAt": {"integerValue": "123"},
        "timetables": {"arrayValue": {"values": [
            {"mapValue": {"fields": {
                "id": {"stringValue": tid},
                "name": {"stringValue": tname},
                "lessons": {"arrayValue": {"values": lessons}},
            }}}
            for tid, tname, lessons in tables
        ]}},
    }}


SAMPLE = _fs_doc("t2", [
    ("t1", "옛 시간표", [_fs_lesson("과학", "담임", "과학실", "3-진", "화", 2)]),
    ("t2", "2026 기본 시간표", [
        _fs_lesson("국어", "담임", "교실", "1-진", "월", 1),
        _fs_lesson("체육", "1-3학년 체육", "체육관", "1-진", "월", 2),
        _fs_lesson("영어", "1/2학년 영어R", "A어학실", "1-선", "월", 1),
        _fs_lesson("음악", "1-3학년 음악", "음악실", "1-진", "화", 1),
    ]),
])


def test_constants():
    assert DAYS == ["월", "화", "수", "목", "금"]
    assert PERIODS == [1, 2, 3, 4, 5, 6, 7]


def test_parse_selects_active_table():
    out = parse_global_state(SAMPLE)
    assert out["table_name"] == "2026 기본 시간표"
    assert len(out["lessons"]) == 4
    first = out["lessons"][0]
    assert first == {"name": "국어", "teacher": "담임", "room": "교실",
                     "classId": "1-진", "day": "월", "period": 1}


def test_parse_falls_back_to_first_table():
    doc = _fs_doc("없는ID", [("t1", "유일", [_fs_lesson("수학", "담임", "교실", "2-미", "수", 3)])])
    out = parse_global_state(doc)
    assert out["table_name"] == "유일"
    assert out["lessons"][0]["period"] == 3


def test_parse_empty_doc():
    assert parse_global_state({}) == {"table_name": "", "lessons": []}


def test_filter_lessons_by_class():
    lessons = parse_global_state(SAMPLE)["lessons"]
    grid = filter_lessons(lessons, "class", "1-진")
    assert set(grid.keys()) == {("월", 1), ("월", 2), ("화", 1)}
    assert grid[("월", 1)][0]["name"] == "국어"


def test_filter_lessons_by_room_and_teacher():
    lessons = parse_global_state(SAMPLE)["lessons"]
    assert list(filter_lessons(lessons, "room", "체육관"))[0] == ("월", 2)
    assert list(filter_lessons(lessons, "teacher", "1/2학년 영어R"))[0] == ("월", 1)


def test_cell_text_class_view_shows_special_room():
    entries = [{"name": "체육", "room": "체육관", "classId": "1-진"}]
    assert cell_text(entries, "class") == "체육📍체육관"
    entries2 = [{"name": "국어", "room": "교실", "classId": "1-진"}]
    assert cell_text(entries2, "class") == "국어"


def test_cell_text_other_views_show_class_and_merge():
    entries = [
        {"name": "영어", "room": "A어학실", "classId": "1-선"},
        {"name": "영어", "room": "A어학실", "classId": "1-진"},
    ]
    assert cell_text(entries, "room") == "1-선/1-진"
    assert cell_text([], "class") == ""


def test_cell_text_overflow():
    entries = [{"name": f"과목{i}", "room": "교실", "classId": f"{i}-진"} for i in range(5)]
    text = cell_text(entries, "class")
    assert "외 2" in text


def test_derive_targets_sorted_unique():
    lessons = parse_global_state(SAMPLE)["lessons"]
    targets = derive_targets(lessons)
    assert targets["class"] == ["1-선", "1-진"]
    assert "체육관" in targets["room"]
    assert "1-3학년 체육" in targets["teacher"]
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `.venv/Scripts/python.exe -m pytest tests/test_timetable.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: 최소 구현 작성**

`src/teacher_widgets/widgets/timetable.py`:
```python
"""시간표 위젯: Firestore 문서 파싱/필터 순수 함수 + 다이얼로그 + GUI.

이 파일의 상단부(순수 함수)는 Task 2, TargetDialog는 Task 3,
FetchWorker·TimetableWidget은 Task 4~5에서 추가된다.
"""

from __future__ import annotations

DAYS = ["월", "화", "수", "목", "금"]
PERIODS = [1, 2, 3, 4, 5, 6, 7]

_VIEW_KEY = {"class": "classId", "room": "room", "teacher": "teacher"}


def _sv(fields: dict, key: str, default: str = "") -> str:
    return fields.get(key, {}).get("stringValue", default)


def parse_global_state(fs_doc: dict) -> dict:
    """Firestore 문서에서 활성 시간표의 경량 lessons를 추출."""
    fields = fs_doc.get("fields", {})
    active_id = _sv(fields, "activeTableId")
    tables = fields.get("timetables", {}).get("arrayValue", {}).get("values", [])

    chosen = None
    for t in tables:
        tf = t.get("mapValue", {}).get("fields", {})
        if _sv(tf, "id") == active_id:
            chosen = tf
            break
    if chosen is None and tables:
        chosen = tables[0].get("mapValue", {}).get("fields", {})
    if chosen is None:
        return {"table_name": "", "lessons": []}

    lessons = []
    for lv in chosen.get("lessons", {}).get("arrayValue", {}).get("values", []):
        lf = lv.get("mapValue", {}).get("fields", {})
        day = _sv(lf, "day")
        period_raw = lf.get("period", {}).get("integerValue")
        if not day or period_raw is None:
            continue
        lessons.append({
            "name": _sv(lf, "name"),
            "teacher": _sv(lf, "teacher"),
            "room": _sv(lf, "room"),
            "classId": _sv(lf, "classId"),
            "day": day,
            "period": int(period_raw),
        })
    return {"table_name": _sv(chosen, "name"), "lessons": lessons}


def filter_lessons(lessons: list, view_type: str, target: str) -> dict:
    """뷰 유형·대상으로 필터해 {(day, period): [lesson...]} 반환."""
    key = _VIEW_KEY[view_type]
    grid: dict = {}
    for lesson in lessons:
        if lesson.get(key) == target:
            grid.setdefault((lesson["day"], lesson["period"]), []).append(lesson)
    return grid


def cell_text(entries: list, view_type: str) -> str:
    """한 칸의 표시 문자열. 웹앱 표시 규칙 계승."""
    if not entries:
        return ""
    parts = []
    for e in entries[:3]:
        if view_type == "class":
            room = e.get("room", "")
            name = e.get("name", "")
            parts.append(f"{name}📍{room}" if room and room != "교실" else name)
        else:
            parts.append(e.get("classId") or e.get("name", ""))
    text = "/".join(parts)
    if len(entries) > 3:
        text += f" 외 {len(entries) - 3}"
    return text


def derive_targets(lessons: list) -> dict:
    """캐시된 lessons에서 뷰별 대상 목록을 유도(정렬·중복 제거·빈값 제외)."""
    out = {"class": set(), "room": set(), "teacher": set()}
    for lesson in lessons:
        if lesson.get("classId"):
            out["class"].add(lesson["classId"])
        if lesson.get("room"):
            out["room"].add(lesson["room"])
        if lesson.get("teacher"):
            out["teacher"].add(lesson["teacher"])
    return {k: sorted(v) for k, v in out.items()}
```

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `.venv/Scripts/python.exe -m pytest tests/test_timetable.py -v`
Expected: 10 passed

- [ ] **Step 5: 전체 스위트 + 커밋**

Run: `.venv/Scripts/python.exe -m pytest -q` → 86 passed 예상.
```bash
git add src/teacher_widgets/widgets/timetable.py tests/test_timetable.py
git commit -m "feat: 시간표 Firestore 파싱·뷰 필터·셀 병합·대상 유도 순수 함수

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: 대상 선택 다이얼로그 (TargetDialog)

**Files:**
- Modify: `src/teacher_widgets/widgets/timetable.py` (TargetDialog 추가)
- Test: `tests/test_timetable.py` (추가)

**Interfaces:**
- Consumes: PySide6, `derive_targets` 출력 형식.
- Produces: `class TargetDialog(QtWidgets.QDialog)`
  - `__init__(targets: dict, view_type: str, target: str, parent=None)` — targets는 `derive_targets` 반환 형식
  - 라디오 3개: `class_radio`, `room_radio`, `teacher_radio` (라벨: 학급/특별실/전담)
  - 콤보: `target_combo` — 선택된 유형의 목록 표시, 유형 전환 시 목록 교체
  - `values() -> tuple[str, str]` → (view_type, target)

- [ ] **Step 1: 실패하는 테스트 작성 (test_timetable.py에 추가)**

```python
from PySide6 import QtWidgets  # 파일 상단에 추가

from teacher_widgets.widgets.timetable import TargetDialog

TARGETS = {"class": ["1-진", "1-선"], "room": ["체육관"], "teacher": ["컴퓨터"]}


def test_target_dialog_initial_state(qtbot):
    dlg = TargetDialog(TARGETS, "class", "1-선")
    qtbot.addWidget(dlg)
    assert dlg.class_radio.isChecked()
    assert dlg.target_combo.currentText() == "1-선"
    assert dlg.values() == ("class", "1-선")


def test_target_dialog_switch_type_repopulates(qtbot):
    dlg = TargetDialog(TARGETS, "class", "1-진")
    qtbot.addWidget(dlg)
    dlg.room_radio.setChecked(True)
    items = [dlg.target_combo.itemText(i) for i in range(dlg.target_combo.count())]
    assert items == ["체육관"]
    assert dlg.values() == ("room", "체육관")


def test_target_dialog_unknown_target_defaults_first(qtbot):
    dlg = TargetDialog(TARGETS, "class", "9-없음")
    qtbot.addWidget(dlg)
    assert dlg.values() == ("class", "1-진")
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `.venv/Scripts/python.exe -m pytest tests/test_timetable.py -k target_dialog -v`
Expected: FAIL (ImportError: TargetDialog)

- [ ] **Step 3: 구현 — timetable.py에 추가**

파일 상단 import에 추가:
```python
from PySide6 import QtWidgets
```

클래스 추가:
```python
class TargetDialog(QtWidgets.QDialog):
    """시간표 대상 선택: 유형(학급/특별실/전담) + 대상 콤보."""

    def __init__(self, targets: dict, view_type: str, target: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("대상 변경")
        self._targets = targets

        layout = QtWidgets.QVBoxLayout(self)

        radios = QtWidgets.QHBoxLayout()
        self.class_radio = QtWidgets.QRadioButton("학급")
        self.room_radio = QtWidgets.QRadioButton("특별실")
        self.teacher_radio = QtWidgets.QRadioButton("전담")
        for r in (self.class_radio, self.room_radio, self.teacher_radio):
            radios.addWidget(r)
            r.toggled.connect(self._repopulate)
        layout.addLayout(radios)

        self.target_combo = QtWidgets.QComboBox()
        layout.addWidget(self.target_combo)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        {"class": self.class_radio, "room": self.room_radio,
         "teacher": self.teacher_radio}.get(view_type, self.class_radio).setChecked(True)
        idx = self.target_combo.findText(target)
        if idx >= 0:
            self.target_combo.setCurrentIndex(idx)

    def _current_type(self) -> str:
        if self.room_radio.isChecked():
            return "room"
        if self.teacher_radio.isChecked():
            return "teacher"
        return "class"

    def _repopulate(self, checked: bool) -> None:
        if not checked:
            return  # 해제 시그널은 무시(전환 시 두 번 호출 방지)
        self.target_combo.clear()
        self.target_combo.addItems(self._targets.get(self._current_type(), []))

    def values(self) -> tuple[str, str]:
        return self._current_type(), self.target_combo.currentText()
```

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `.venv/Scripts/python.exe -m pytest tests/test_timetable.py -v`
Expected: 순수 10 + 다이얼로그 3 = 13 passed.

- [ ] **Step 5: 커밋**

```bash
git add src/teacher_widgets/widgets/timetable.py tests/test_timetable.py
git commit -m "feat: 시간표 대상 선택 다이얼로그(유형 라디오+콤보)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: FetchWorker + TimetableWidget (GUI)

**Files:**
- Modify: `src/teacher_widgets/widgets/timetable.py` (FetchWorker, TimetableWidget 추가)
- Test: `tests/test_timetable.py` (위젯 테스트 추가)

**Interfaces:**
- Consumes: `BaseWidget`(`_custom_menu_actions` 훅 포함), `ConfigStore`, `responsive.scale_factor/scaled_font_pt`, `data_remote`(anon_sign_in/firestore_get_document/read_cache/write_cache), Task 2~3 산출물.
- Produces:
  - `class FetchWorker(QtCore.QThread)` — `__init__(settings: dict)`, 시그널 `finished_ok(dict)`, `failed(str)`. run(): 인증→GET→`parse_global_state`→`fetched_at` 부착→emit.
  - `class TimetableWidget(BaseWidget)` (widget_name="timetable", BASE_SIZE=(340, 330))
    - `cache_path: Path` (store.path.parent / "cache" / "timetable.json")
    - `apply_data(data: dict) -> None` (캐시 저장 + 그리드 렌더)
    - `render_grid() -> None` (현재 데이터·대상으로 5×7 라벨 갱신, 오늘 요일 열 강조)
    - `refresh() -> None` (FetchWorker 시작; 이미 동작 중이면 무시)
    - `_on_fetch_ok(data)` / `_on_fetch_failed(msg)` (상태 라벨 갱신)
    - `change_target() -> None` (TargetDialog → config 저장 → render_grid)
    - `_custom_menu_actions(menu)` → {대상 변경, 새로고침}
    - `mouseDoubleClickEvent` → `open_webapp()` (Task 5에서 구현; Task 4에서는 메서드 존재만 — pass)
    - 속성: `header_label`, `status_label`, `_cells: dict[tuple[str,int], QLabel]`, `_data: dict|None`

- [ ] **Step 1: 실패하는 테스트 작성 (test_timetable.py에 추가)**

```python
import json

from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.widgets.timetable import TimetableWidget

CACHE_DATA = {
    "fetched_at": "2026-07-02T10:00:00",
    "table_name": "2026 기본 시간표",
    "lessons": [
        {"name": "국어", "teacher": "담임", "room": "교실",
         "classId": "1-진", "day": "월", "period": 1},
        {"name": "체육", "teacher": "1-3학년 체육", "room": "체육관",
         "classId": "1-진", "day": "화", "period": 2},
    ],
}


def make_widget(qtbot, tmp_path, cache=CACHE_DATA):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    if cache is not None:
        cache_file = tmp_path / "cache" / "timetable.json"
        cache_file.parent.mkdir(parents=True)
        cache_file.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    w = TimetableWidget(store)
    qtbot.addWidget(w)
    return store, w


def test_widget_loads_cache_and_renders(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path)
    assert w.widget_name == "timetable"
    assert "1-진" in w.header_label.text()
    assert w._cells[("월", 1)].text() == "국어"
    assert w._cells[("화", 2)].text() == "체육📍체육관"
    assert w._cells[("금", 7)].text() == ""


def test_widget_without_cache_shows_empty_state(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path, cache=None)
    assert "새로고침" in w.status_label.text() or "데이터 없음" in w.status_label.text()


def test_apply_data_writes_cache_and_rerenders(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path, cache=None)
    w.apply_data(CACHE_DATA)
    assert w._cells[("월", 1)].text() == "국어"
    saved = json.loads((tmp_path / "cache" / "timetable.json").read_text(encoding="utf-8"))
    assert saved["table_name"] == "2026 기본 시간표"


def test_change_target_updates_config_and_grid(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path)
    # 다이얼로그 우회: 내부 상태 직접 적용 경로 검증
    w._set_target("room", "체육관")
    assert store.data["timetable"]["view_type"] == "room"
    assert store.data["timetable"]["target"] == "체육관"
    assert w._cells[("화", 2)].text() == "1-진"


def test_fetch_failed_sets_status(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path)
    w._on_fetch_failed("timeout")
    assert "갱신 실패" in w.status_label.text()
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `.venv/Scripts/python.exe -m pytest tests/test_timetable.py -k widget -v`
Expected: FAIL (ImportError: TimetableWidget)

- [ ] **Step 3: 구현 — timetable.py에 추가**

import 보강 (기존 `from PySide6 import QtWidgets` 교체):
```python
import datetime
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from teacher_widgets.core.base_widget import BaseWidget
from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.core.data_remote import (
    anon_sign_in,
    firestore_get_document,
    read_cache,
    write_cache,
)
from teacher_widgets.core.responsive import scale_factor, scaled_font_pt
```

클래스 추가:
```python
class FetchWorker(QtCore.QThread):
    """백그라운드에서 익명 인증→문서 GET→경량 파싱. GUI 블로킹 금지."""

    finished_ok = QtCore.Signal(dict)
    failed = QtCore.Signal(str)

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self._settings = dict(settings)

    def run(self) -> None:
        try:
            token = anon_sign_in(self._settings["api_key"])
            doc_path = (
                f"artifacts/{self._settings['artifact_app_id']}"
                "/public/data/timetables_state/global_state"
            )
            doc = firestore_get_document(self._settings["project_id"], doc_path, token)
            data = parse_global_state(doc)
            data["fetched_at"] = datetime.datetime.now().isoformat(timespec="seconds")
            self.finished_ok.emit(data)
        except Exception as exc:  # 네트워크·파싱 어떤 실패든 위젯을 죽이지 않는다
            self.failed.emit(str(exc))


class TimetableWidget(BaseWidget):
    BASE_SIZE = (340, 330)

    def __init__(self, store: ConfigStore):
        super().__init__("timetable", store)
        self.cache_path = Path(store.path).parent / "cache" / "timetable.json"
        self._data: dict | None = None
        self._worker: FetchWorker | None = None
        self._cells: dict[tuple[str, int], QtWidgets.QLabel] = {}

        self.header_label = QtWidgets.QLabel("", alignment=QtCore.Qt.AlignCenter)
        self.header_label.setStyleSheet("font-weight:700; color:#2b2b2b;")
        self.status_label = QtWidgets.QLabel("", alignment=QtCore.Qt.AlignCenter)
        self.status_label.setStyleSheet("color:#999;")
        self.content_layout.addWidget(self.header_label)
        self.content_layout.addWidget(self.status_label)

        grid_container = QtWidgets.QWidget()
        self.grid_layout = QtWidgets.QGridLayout(grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(2)
        for col, day in enumerate(DAYS):
            head = QtWidgets.QLabel(day, alignment=QtCore.Qt.AlignCenter)
            head.setStyleSheet("color:#666; font-weight:600;")
            self.grid_layout.addWidget(head, 0, col + 1)
        for row, period in enumerate(PERIODS):
            num = QtWidgets.QLabel(str(period), alignment=QtCore.Qt.AlignCenter)
            num.setStyleSheet("color:#999;")
            self.grid_layout.addWidget(num, row + 1, 0)
            for col, day in enumerate(DAYS):
                cell = QtWidgets.QLabel("", alignment=QtCore.Qt.AlignCenter)
                cell.setWordWrap(True)
                self._cells[(day, period)] = cell
                self.grid_layout.addWidget(cell, row + 1, col + 1)
        self.content_layout.addWidget(grid_container, stretch=1)

        cached = read_cache(self.cache_path)
        if cached is not None:
            self._data = cached
            self.render_grid()
            self.status_label.setText(f"갱신: {cached.get('fetched_at', '')[:16]}")
        else:
            self.status_label.setText("데이터 없음 — 우클릭 → 새로고침")

        self._refresh_timer = QtCore.QTimer(self)
        minutes = int(self.store.data["timetable"].get("refresh_minutes", 60))
        self._refresh_timer.timeout.connect(self.refresh)
        self._refresh_timer.start(minutes * 60 * 1000)
        self.refresh()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(QtGui.QColor(255, 255, 255, 235))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 16, 16)

    # --- 데이터 ---
    def refresh(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        self._worker = FetchWorker(self.store.data["timetable"], self)
        self._worker.finished_ok.connect(self._on_fetch_ok)
        self._worker.failed.connect(self._on_fetch_failed)
        self._worker.start()

    def _on_fetch_ok(self, data: dict) -> None:
        self.apply_data(data)
        self.status_label.setText(f"갱신: {data.get('fetched_at', '')[:16]}")

    def _on_fetch_failed(self, msg: str) -> None:
        self.status_label.setText("갱신 실패 — 캐시 표시 중")

    def apply_data(self, data: dict) -> None:
        self._data = data
        write_cache(self.cache_path, data)
        self.render_grid()

    # --- 렌더 ---
    def render_grid(self) -> None:
        settings = self.store.data["timetable"]
        view_type = settings.get("view_type", "class")
        target = settings.get("target", "")
        self.header_label.setText(f"{target} 시간표")

        lessons = (self._data or {}).get("lessons", [])
        grid = filter_lessons(lessons, view_type, target)
        today = DAYS[datetime.date.today().weekday()] if datetime.date.today().weekday() < 5 else None
        for (day, period), cell in self._cells.items():
            cell.setText(cell_text(grid.get((day, period), []), view_type))
            base = "background:rgba(124,198,166,0.18); border-radius:4px;" if day == today else ""
            cell.setStyleSheet(f"color:#2b2b2b; {base}")
        self._apply_responsive()

    def _set_target(self, view_type: str, target: str) -> None:
        self.store.data["timetable"]["view_type"] = view_type
        self.store.data["timetable"]["target"] = target
        self.store.save()
        self.render_grid()

    # --- 메뉴 ---
    def _custom_menu_actions(self, menu) -> dict:
        target_action = menu.addAction("대상 변경")
        refresh_action = menu.addAction("새로고침")
        return {target_action: self.change_target, refresh_action: self.refresh}

    def change_target(self) -> None:
        lessons = (self._data or {}).get("lessons", [])
        targets = derive_targets(lessons)
        settings = self.store.data["timetable"]
        dlg = TargetDialog(targets, settings.get("view_type", "class"),
                           settings.get("target", ""), self)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            view_type, target = dlg.values()
            if target:
                self._set_target(view_type, target)

    # --- 웹앱 (Task 5에서 구현) ---
    def open_webapp(self) -> None:
        pass

    def mouseDoubleClickEvent(self, event) -> None:
        self.open_webapp()
        event.accept()

    # --- 반응형 ---
    def _apply_responsive(self) -> None:
        factor = scale_factor((self.width(), self.height()), self.BASE_SIZE)
        cell_pt = scaled_font_pt(8, factor)
        for cell in self._cells.values():
            style = cell.styleSheet()
            # font-size만 갱신 (오늘 강조 배경 유지)
            base = style.split("font-size")[0]
            cell.setStyleSheet(f"{base} font-size:{cell_pt}pt;")
        self.header_label.setStyleSheet(
            f"font-weight:700; color:#2b2b2b; font-size:{scaled_font_pt(12, factor)}pt;"
        )
        self.status_label.setStyleSheet(
            f"color:#999; font-size:{scaled_font_pt(8, factor)}pt;"
        )

    def on_resized(self, width: int, height: int) -> None:
        self._apply_responsive()
```

**주의:** 테스트는 offscreen에서 실행되며 `refresh()`가 FetchWorker(실 네트워크)를 시작한다. 테스트가 네트워크에 의존하지 않도록: FetchWorker는 시작되어도 결과가 오기 전 테스트가 끝나고, 실패해도 status만 바뀐다. 그러나 **테스트 결정성**을 위해 `__init__` 마지막의 `self.refresh()`는 다음 가드로 감싼다:
```python
        if not self.store.data["timetable"].get("_skip_initial_fetch", False):
            self.refresh()
```
그리고 테스트 `make_widget`에서 store 생성 직후 `store.data["timetable"]["_skip_initial_fetch"] = True`를 설정한다 (Step 1 테스트 코드의 `store.load()` 다음 줄에 추가). 프로덕션 기본값에는 이 키가 없어 정상 fetch가 동작한다.

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `.venv/Scripts/python.exe -m pytest tests/test_timetable.py -v`
Expected: 13 + 위젯 5 = 18 passed. (네트워크 호출 없음 확인 — `_skip_initial_fetch` 가드)

- [ ] **Step 5: 전체 스위트 + 커밋**

Run: `.venv/Scripts/python.exe -m pytest -q` → 94 passed 예상.
```bash
git add src/teacher_widgets/widgets/timetable.py tests/test_timetable.py
git commit -m "feat: 시간표 위젯(백그라운드 갱신·캐시·5x7 그리드·오늘 강조)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: 웹앱 앱모드 실행 + 런처 등록

**Files:**
- Modify: `src/teacher_widgets/widgets/timetable.py` (build_app_command + open_webapp 구현)
- Modify: `src/teacher_widgets/main.py` (timetable 등록)
- Test: `tests/test_timetable.py` (build_app_command 테스트)

**Interfaces:**
- Consumes: Task 4의 TimetableWidget.
- Produces:
  - `build_app_command(url: str) -> list[str] | None` (msedge→chrome 순으로 shutil.which; 없으면 None)
  - `TimetableWidget.open_webapp()` 구현: 이전 프로세스 생존 시 재사용(창 앞으로 best-effort), 아니면 실행. 명령 없으면 `webbrowser.open(url)`.
  - main.py에 `registry.register("timetable", lambda: TimetableWidget(store))`

- [ ] **Step 1: 실패하는 테스트 작성 (test_timetable.py에 추가)**

```python
from teacher_widgets.widgets import timetable as tt_mod
from teacher_widgets.widgets.timetable import build_app_command


def test_build_app_command_prefers_edge(monkeypatch):
    monkeypatch.setattr(tt_mod.shutil, "which",
                        lambda exe: r"C:\edge\msedge.exe" if exe == "msedge" else None)
    cmd = build_app_command("https://example.com/")
    assert cmd == [r"C:\edge\msedge.exe", "--app=https://example.com/"]


def test_build_app_command_falls_back_to_chrome(monkeypatch):
    monkeypatch.setattr(tt_mod.shutil, "which",
                        lambda exe: r"C:\chrome\chrome.exe" if exe == "chrome" else None)
    cmd = build_app_command("https://example.com/")
    assert cmd[0].endswith("chrome.exe")


def test_build_app_command_none_when_no_browser(monkeypatch):
    monkeypatch.setattr(tt_mod.shutil, "which", lambda exe: None)
    assert build_app_command("https://example.com/") is None
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `.venv/Scripts/python.exe -m pytest tests/test_timetable.py -k app_command -v`
Expected: FAIL (ImportError: build_app_command)

- [ ] **Step 3: 구현**

`timetable.py` import에 추가:
```python
import shutil
import subprocess
import webbrowser
```

모듈 함수 추가:
```python
def build_app_command(url: str) -> list[str] | None:
    """앱 모드(--app) 실행 명령. Edge 우선, Chrome 차선, 없으면 None."""
    for exe in ("msedge", "chrome"):
        path = shutil.which(exe)
        if path:
            return [path, f"--app={url}"]
    return None
```

`TimetableWidget.open_webapp`을 다음으로 교체 (`__init__`에 `self._web_proc = None` 추가):
```python
    def open_webapp(self) -> None:
        url = self.store.data["timetable"].get("webapp_url", "")
        if not url:
            return
        # 이전에 띄운 앱 창이 살아있으면 맨 앞으로 (best-effort)
        if self._web_proc is not None and self._web_proc.poll() is None:
            self._bring_web_to_front()
            return
        cmd = build_app_command(url)
        if cmd:
            self._web_proc = subprocess.Popen(cmd)
        else:
            webbrowser.open(url)

    def _bring_web_to_front(self) -> None:
        """자식 프로세스의 최상위 창을 앞으로. 실패해도 무해(best-effort)."""
        try:
            import ctypes

            user32 = ctypes.windll.user32
            pid = self._web_proc.pid

            @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
            def enum_handler(hwnd, _lparam):
                found_pid = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(found_pid))
                if found_pid.value == pid and user32.IsWindowVisible(hwnd):
                    user32.SetForegroundWindow(hwnd)
                    return False  # 중단
                return True

            user32.EnumWindows(enum_handler, 0)
        except Exception:
            pass  # 브라우저가 기존 프로세스에 위임한 경우 등 — 조용히 무시
```

`main.py`: import에 `from .widgets.timetable import TimetableWidget` 추가, checklist 등록 다음에:
```python
    registry.register("timetable", lambda: TimetableWidget(store))
```

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `.venv/Scripts/python.exe -m pytest tests/test_timetable.py -v`
Expected: 18 + 3 = 21 passed.

- [ ] **Step 5: 실 데이터 수동 스모크 (1회)**

Run (비차단, offscreen — 실제 Firestore 호출):
```bash
QT_QPA_PLATFORM=offscreen PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "
import sys, tempfile, os; sys.path.insert(0, 'src')
from PySide6 import QtWidgets, QtCore
app = QtWidgets.QApplication([])
from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.widgets.timetable import TimetableWidget
d = tempfile.mkdtemp(); s = ConfigStore(os.path.join(d, 'c.json')); s.load()
w = TimetableWidget(s)
def check():
    print('status:', w.status_label.text())
    print('cell 월1:', repr(w._cells[('월', 1)].text()))
    app.quit()
QtCore.QTimer.singleShot(8000, check)
app.exec()
"
```
Expected: `status: 갱신: 2026-07-02T...` + 월요일 1교시 셀에 실제 과목명. (네트워크 불가 환경이면 "갱신 실패" — 그 경우 보고에 명시)

- [ ] **Step 6: 전체 스위트 + 커밋**

Run: `.venv/Scripts/python.exe -m pytest -q` → 97 passed 예상.
```bash
git add src/teacher_widgets/widgets/timetable.py src/teacher_widgets/main.py tests/test_timetable.py
git commit -m "feat: 시간표 더블클릭 앱모드 실행과 런처 등록

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 자기 점검 (Self-Review)

**1. Spec 커버리지**
- 익명 인증 + Firestore REST + 문서 경로 → Task 1 (data_remote) ✅
- 경량 파싱(활성 시간표 lessons만) + fallback(첫 시간표/빈) → Task 2 ✅
- 캐시 파일(cache/timetable.json, config 오염 금지) → Task 1(read/write) + Task 4(cache_path·apply_data) ✅
- 갱신: 시작 시 + 주기(refresh_minutes) + 메뉴 새로고침 → Task 4 ✅
- 실패 처리(캐시 유지 + "갱신 실패", 캐시 없음 안내, GUI 비블로킹) → Task 4 (FetchWorker + status) ✅
- 대상 선택(유형+콤보, 데이터 유도, config 저장) → Task 2(derive_targets) + Task 3 + Task 4(change_target/_set_target) ✅
- 표시(5×7, 오늘 강조, 셀 규칙, 반응형) → Task 2(cell_text) + Task 4(render_grid/_apply_responsive) ✅
- 더블클릭 → 앱모드(Edge→Chrome→기본), 생존 시 앞으로 → Task 5 ✅
- config 기본값(공개 웹 키) → Task 1 ✅
- 테스트 전략(픽스처·캐시 주입·네트워크 금지) → 각 Task + `_skip_initial_fetch` 가드 ✅
- 엣지(시간표 0개, 대상 소멸→빈 그리드) → Task 2 parse fallback + render는 빈 grid 허용 ✅

**2. 플레이스홀더 스캔:** 없음 — 모든 코드 스텝에 실제 코드 ✅ (Task 4의 open_webapp `pass`는 Task 5에서 구현되는 명시적 단계)

**3. 타입 일관성:** `parse_global_state->dict{table_name,lessons}`, `filter_lessons(lessons,view_type,target)->dict[(day,period),list]`, `cell_text(entries,view_type)->str`, `derive_targets(lessons)->dict`, `TargetDialog(targets,view_type,target)`, `values()->(str,str)`, `FetchWorker(settings)`, `TimetableWidget(store)`, `build_app_command(url)->list|None` — Task 간 일치 ✅

**범위 밖:** 현재 교시 강조(Phase 5 연동), updatedAt 조건부 갱신, 다중 시간표 선택 UI.
