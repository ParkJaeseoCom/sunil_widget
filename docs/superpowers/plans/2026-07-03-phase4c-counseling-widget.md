# Phase 4-C 상담기록 위젯 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 원문+로컬 규칙 정제본+자동 타임스탬프 3요소로 지도 기록을 보관하고 Excel로 내보내는 완전 로컬 상담기록 위젯.

**Architecture:** 정제 규칙·항목 헬퍼·Excel 빌더는 순수 함수(픽스처 테스트), 저장은 4-B의 `data_local` 재사용, GUI는 BaseWidget 상속(입력줄+시간 역순 목록). AI·네트워크 없음.

**Tech Stack:** Python 3.14, PySide6, openpyxl(기설치), pytest + pytest-qt.

## Global Constraints

- 파일: `store.path.parent / "counseling.json"`, 구조 `{"entries": [{"ts","raw","refined"}]}`. 저장은 반드시 `data_local.save_json_with_backup`. **외부 전송·AI 금지, 네트워크 import 금지.**
- `ts`는 기록 시 자동(초 ISO), 수정 기능 없음(삭제만).
- 정제 규칙(정확히): 공백 정리 → 끝 문장부호(`.` `!` `?` `…`) 제거 → 말미 "함"이면 `.`만, 아니면 `" 관련 지도함."` 부착. 빈/공백 입력 → `""`.
- 목록 표시 `MM/DD HH:MM  원문(60자 축약)`, 툴팁=정제본, 시간 역순.
- 위젯 식별자 `counseling`. offscreen 테스트, 다이얼로그(QFileDialog/확인팝업)는 훅 오버라이드로 우회.
- 실행 `.venv/Scripts/python.exe -m pytest -v` (경로 따옴표). 커밋 footer: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. 기존 167 테스트 유지.

---

## 파일 구조

```
src/teacher_widgets/widgets/counseling.py  # (신규) 순수부 + CounselingWidget
src/teacher_widgets/main.py                # (수정) counseling 등록
tests/test_counseling.py                   # (신규)
tests/test_tray.py                         # (수정) 등록 확인 1개
```

---

## Task 1: 정제 규칙 + 항목 헬퍼 + Excel 빌더 (순수)

**Files:**
- Create: `src/teacher_widgets/widgets/counseling.py` (순수부)
- Test: `tests/test_counseling.py`

**Interfaces:**
- Consumes: openpyxl.
- Produces:
  - `refine_text(raw: str) -> str` (Global Constraints 규칙)
  - `add_entry(data: dict, raw: str, now: datetime.datetime | None = None) -> dict | None` — 빈 정제 결과면 None(기록 거부); 성공 시 entry dict 반환(entries에 append; ts는 now or 현재, `isoformat(timespec="seconds")`)
  - `delete_entry(data: dict, ts: str) -> bool` — 해당 ts 첫 항목 제거
  - `sorted_entries(data: dict) -> list[dict]` — ts 내림차순(동률은 원 순서 역순 아님 — 안정 정렬 내림차순)
  - `summary_line(entry: dict, limit: int = 60) -> str` — `"MM/DD HH:MM  원문축약"`
  - `build_counseling_workbook(entries: list[dict]) -> openpyxl.Workbook` — 시트 "상담기록", 1행 헤더 `["일시","원문","정제본"]`, 이후 시간 역순 행, 열 너비 A=18/B=50/C=55

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_counseling.py`:
```python
import datetime

from teacher_widgets.widgets.counseling import (
    refine_text,
    add_entry,
    delete_entry,
    sorted_entries,
    summary_line,
    build_counseling_workbook,
)


def test_refine_appends_template():
    assert refine_text("복도에서 뛰어다님 주의") == "복도에서 뛰어다님 주의 관련 지도함."


def test_refine_keeps_ham_ending():
    assert refine_text("수업 태도에 대해 지도함") == "수업 태도에 대해 지도함."
    assert refine_text("보호자에게 안내함.") == "보호자에게 안내함."


def test_refine_cleans_whitespace_and_punct():
    assert refine_text("  줄넘기   분실 !  ") == "줄넘기 분실 관련 지도함."
    assert refine_text("자리 이동…") == "자리 이동 관련 지도함."


def test_refine_empty_returns_empty():
    assert refine_text("   ") == ""
    assert refine_text("") == ""


NOW = datetime.datetime(2026, 7, 3, 14, 30, 0)


def test_add_entry_sets_ts_raw_refined():
    data = {}
    e = add_entry(data, "복도 주의", now=NOW)
    assert e == {"ts": "2026-07-03T14:30:00", "raw": "복도 주의",
                 "refined": "복도 주의 관련 지도함."}
    assert data["entries"] == [e]


def test_add_entry_rejects_blank():
    data = {}
    assert add_entry(data, "   ", now=NOW) is None
    assert data.get("entries", []) == []


def test_delete_and_sorted():
    data = {}
    add_entry(data, "첫째", now=datetime.datetime(2026, 7, 1, 9, 0, 0))
    add_entry(data, "둘째", now=datetime.datetime(2026, 7, 2, 9, 0, 0))
    out = sorted_entries(data)
    assert [e["raw"] for e in out] == ["둘째", "첫째"]  # 시간 역순
    assert delete_entry(data, "2026-07-01T09:00:00") is True
    assert delete_entry(data, "2026-07-01T09:00:00") is False
    assert [e["raw"] for e in sorted_entries(data)] == ["둘째"]


def test_summary_line_truncates():
    e = {"ts": "2026-07-03T14:30:00", "raw": "가" * 100, "refined": "x"}
    line = summary_line(e)
    assert line.startswith("07/03 14:30  ")
    assert line.endswith("…")
    assert len(line) <= 13 + 61


def test_workbook():
    entries = [
        {"ts": "2026-07-02T09:00:00", "raw": "둘째", "refined": "둘째 관련 지도함."},
        {"ts": "2026-07-01T09:00:00", "raw": "첫째", "refined": "첫째 관련 지도함."},
    ]
    wb = build_counseling_workbook(entries)
    ws = wb["상담기록"]
    assert [ws.cell(row=1, column=c).value for c in (1, 2, 3)] == ["일시", "원문", "정제본"]
    assert ws.cell(row=2, column=1).value == "2026-07-02T09:00:00"
    assert ws.cell(row=3, column=2).value == "첫째"
```

- [ ] **Step 2: RED 확인** — `.venv/Scripts/python.exe -m pytest tests/test_counseling.py -v` → ModuleNotFoundError

- [ ] **Step 3: 구현**

`src/teacher_widgets/widgets/counseling.py`:
```python
"""상담·지도 기록 위젯: 원문+정제본+타임스탬프 — 완전 로컬(외부 전송·AI 없음).

순수부(정제·헬퍼·Excel)는 Task 1, GUI는 Task 2.
"""

from __future__ import annotations

import datetime
import re

from openpyxl import Workbook

_WS_RE = re.compile(r"\s+")
_TRAIL_PUNCT_RE = re.compile(r"[.!?…\s]+$")


def refine_text(raw: str) -> str:
    """로컬 규칙 정제: 공백 정리 → 끝 문장부호 제거 → '지도함' 템플릿."""
    cleaned = _WS_RE.sub(" ", raw).strip()
    if not cleaned:
        return ""
    cleaned = _TRAIL_PUNCT_RE.sub("", cleaned)
    if cleaned.endswith("함"):
        return cleaned + "."
    return cleaned + " 관련 지도함."


def add_entry(data: dict, raw: str,
              now: datetime.datetime | None = None) -> dict | None:
    refined = refine_text(raw)
    if not refined:
        return None
    ts = (now or datetime.datetime.now()).isoformat(timespec="seconds")
    entry = {"ts": ts, "raw": _WS_RE.sub(" ", raw).strip(), "refined": refined}
    data.setdefault("entries", []).append(entry)
    return entry


def delete_entry(data: dict, ts: str) -> bool:
    entries = data.get("entries", [])
    for i, e in enumerate(entries):
        if e.get("ts") == ts:
            del entries[i]
            return True
    return False


def sorted_entries(data: dict) -> list[dict]:
    return sorted(data.get("entries", []), key=lambda e: e.get("ts", ""), reverse=True)


def summary_line(entry: dict, limit: int = 60) -> str:
    ts = entry.get("ts", "")
    stamp = f"{ts[5:7]}/{ts[8:10]} {ts[11:16]}" if len(ts) >= 16 else ts
    raw = entry.get("raw", "")
    if len(raw) > limit:
        raw = raw[:limit] + "…"
    return f"{stamp}  {raw}"


def build_counseling_workbook(entries: list[dict]) -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = "상담기록"
    ws.append(["일시", "원문", "정제본"])
    for e in sorted(entries, key=lambda x: x.get("ts", ""), reverse=True):
        ws.append([e.get("ts", ""), e.get("raw", ""), e.get("refined", "")])
    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 50
    ws.column_dimensions["C"].width = 55
    return wb
```

- [ ] **Step 4: GREEN + 전체 스위트** — 176 passed 예상 (167+9).

- [ ] **Step 5: 커밋**

```bash
git add src/teacher_widgets/widgets/counseling.py tests/test_counseling.py
git commit -m "feat: 상담기록 정제 규칙·항목 헬퍼·Excel 빌더

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: CounselingWidget (GUI) + 런처 등록 + 스모크

**Files:**
- Modify: `src/teacher_widgets/widgets/counseling.py`, `src/teacher_widgets/main.py`
- Test: `tests/test_counseling.py` (추가), `tests/test_tray.py` (1개)

**Interfaces:**
- Consumes: Task 1 순수부, `BaseWidget`, `data_local.load/save_json_with_backup`, `responsive`.
- Produces: `class CounselingWidget(BaseWidget)` (widget_name="counseling", BASE_SIZE=(300, 340))
  - `data_path` (store.path.parent/"counseling.json"), `_data: dict`
  - `input_edit: QLineEdit` (returnPressed→`submit_text()`), `list_widget: QListWidget`, `count_label: QLabel`
  - `submit_text() -> bool` — add_entry(None이면 무시·False)→저장→목록 갱신→입력 클리어
  - `refresh_list()` — sorted_entries로 재구성; item의 `Qt.UserRole`=ts, 툴팁=refined
  - `delete_selected(ts: str) -> None` — `_confirm_delete()` 훅(기본 QMessageBox, 테스트 오버라이드) 후 삭제·저장·갱신
  - 항목 우클릭 메뉴: "정제본 복사"(QApplication.clipboard) / "삭제"
  - `_custom_menu_actions`: "Excel 내보내기" → `export_excel()` (QFileDialog 얇게)
  - main.py: weather 등록 다음 `registry.register("counseling", lambda: CounselingWidget(store))`

- [ ] **Step 1: 실패하는 테스트 작성 (test_counseling.py에 추가)**

```python
import json as _json

from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.widgets.counseling import CounselingWidget


def make_widget(qtbot, tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    w = CounselingWidget(store)
    qtbot.addWidget(w)
    return store, w


def test_widget_submit_appends_and_saves(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path)
    w.input_edit.setText("복도 주의")
    assert w.submit_text() is True
    assert w.list_widget.count() == 1
    assert w.input_edit.text() == ""
    saved = _json.loads((tmp_path / "counseling.json").read_text(encoding="utf-8"))
    assert saved["entries"][0]["raw"] == "복도 주의"
    assert "지도함" in saved["entries"][0]["refined"]
    assert "1건" in w.count_label.text()


def test_widget_blank_submit_ignored(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path)
    w.input_edit.setText("   ")
    assert w.submit_text() is False
    assert w.list_widget.count() == 0
    assert not (tmp_path / "counseling.json").exists()


def test_widget_list_desc_and_tooltip(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path)
    import teacher_widgets.widgets.counseling as c
    c.add_entry(w._data, "첫째", now=__import__("datetime").datetime(2026, 7, 1, 9, 0, 0))
    c.add_entry(w._data, "둘째", now=__import__("datetime").datetime(2026, 7, 2, 9, 0, 0))
    w.refresh_list()
    assert "둘째" in w.list_widget.item(0).text()
    assert "지도함" in w.list_widget.item(0).toolTip()


def test_widget_delete_with_confirm_hook(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path)
    w.input_edit.setText("지울 것")
    w.submit_text()
    ts = w.list_widget.item(0).data(32)  # Qt.UserRole == 32
    w._confirm_delete = lambda: True
    w.delete_selected(ts)
    assert w.list_widget.count() == 0
```

`tests/test_tray.py`에 추가:
```python
def test_tray_menu_lists_counseling(qtbot, tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    reg = WidgetRegistry(store)
    reg.register("counseling", lambda: BaseWidget("counseling", store))
    menu = build_tray_menu(reg)
    assert "counseling" in [a.text() for a in menu.actions() if a.text()]
```

- [ ] **Step 2: RED 확인** — ImportError: CounselingWidget

- [ ] **Step 3: 구현 (counseling.py에 추가)**

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
```

클래스:
```python
class CounselingWidget(BaseWidget):
    BASE_SIZE = (300, 340)

    def __init__(self, store: ConfigStore):
        super().__init__("counseling", store)
        self.data_path = Path(store.path).parent / "counseling.json"
        self._data = load_json_with_backup(self.data_path)

        self.header_label = QtWidgets.QLabel("📋 상담·지도 기록",
                                             alignment=QtCore.Qt.AlignCenter)
        self.header_label.setStyleSheet("font-weight:700; color:#2b2b2b;")
        self.count_label = QtWidgets.QLabel("", alignment=QtCore.Qt.AlignCenter)
        self.count_label.setStyleSheet("color:#999;")
        self.content_layout.addWidget(self.header_label)
        self.content_layout.addWidget(self.count_label)

        self.input_edit = QtWidgets.QLineEdit()
        self.input_edit.setPlaceholderText("지도 내용 입력 후 Enter — 시각 자동 기록")
        self.input_edit.returnPressed.connect(self.submit_text)
        self.content_layout.addWidget(self.input_edit)

        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._item_menu)
        self.content_layout.addWidget(self.list_widget, stretch=1)

        self.refresh_list()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(QtGui.QColor(255, 255, 255, 240))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 16, 16)

    # --- 기록 ---
    def _save(self) -> None:
        save_json_with_backup(self.data_path, self._data)

    def submit_text(self) -> bool:
        entry = add_entry(self._data, self.input_edit.text())
        if entry is None:
            return False
        self._save()
        self.input_edit.clear()
        self.refresh_list()
        return True

    def refresh_list(self) -> None:
        self.list_widget.clear()
        entries = sorted_entries(self._data)
        for e in entries:
            item = QtWidgets.QListWidgetItem(summary_line(e))
            item.setData(QtCore.Qt.UserRole, e["ts"])
            item.setToolTip(e.get("refined", ""))
            self.list_widget.addItem(item)
        self.count_label.setText(f"{len(entries)}건 — 로컬에만 저장됨")

    # --- 삭제/복사 ---
    def _confirm_delete(self) -> bool:
        answer = QtWidgets.QMessageBox.question(self, "삭제", "이 기록을 삭제할까요?")
        return answer == QtWidgets.QMessageBox.Yes

    def delete_selected(self, ts: str) -> None:
        if not self._confirm_delete():
            return
        if delete_entry(self._data, ts):
            self._save()
            self.refresh_list()

    def _item_menu(self, pos: QtCore.QPoint) -> None:
        item = self.list_widget.itemAt(pos)
        if item is None:
            return
        ts = item.data(QtCore.Qt.UserRole)
        menu = QtWidgets.QMenu(self)
        copy_action = menu.addAction("정제본 복사")
        delete_action = menu.addAction("삭제")
        chosen = menu.exec(self.list_widget.mapToGlobal(pos))
        if chosen == copy_action:
            QtWidgets.QApplication.clipboard().setText(item.toolTip())
        elif chosen == delete_action:
            self.delete_selected(ts)

    # --- Excel ---
    def export_excel(self) -> None:
        entries = self._data.get("entries", [])
        if not entries:
            self.count_label.setText("내보낼 기록이 없습니다")
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Excel로 내보내기", "상담기록.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        try:
            build_counseling_workbook(entries).save(path)
            self.count_label.setText(f"저장됨: {path}")
        except OSError as exc:
            self.count_label.setText(f"저장 실패: {exc}")

    def _custom_menu_actions(self, menu) -> dict:
        export_action = menu.addAction("Excel 내보내기")
        return {export_action: self.export_excel}

    # --- 반응형 ---
    def _apply_responsive(self) -> None:
        factor = scale_factor((self.width(), self.height()), self.BASE_SIZE)
        self.header_label.setStyleSheet(
            f"font-weight:700; color:#2b2b2b; font-size:{scaled_font_pt(12, factor)}pt;")
        font = self.list_widget.font()
        font.setPointSize(scaled_font_pt(9, factor))
        self.list_widget.setFont(font)

    def on_resized(self, width: int, height: int) -> None:
        self._apply_responsive()
```

`main.py`: import `from .widgets.counseling import CounselingWidget`, weather 다음 `registry.register("counseling", lambda: CounselingWidget(store))`.

- [ ] **Step 4: GREEN + 전체 스위트** — 182 passed 예상 (176+5+1).

- [ ] **Step 5: 비차단 스모크**

```bash
QT_QPA_PLATFORM=offscreen PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "
import sys, tempfile, os; sys.path.insert(0, 'src')
from PySide6 import QtWidgets
app = QtWidgets.QApplication([])
from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.widgets.counseling import CounselingWidget
d = tempfile.mkdtemp(); s = ConfigStore(os.path.join(d, 'c.json')); s.load()
w = CounselingWidget(s)
w.input_edit.setText('테스트 지도'); w.submit_text()
print('OK', w.list_widget.count(), '건 |', w.list_widget.item(0).toolTip())
"
```
Expected: `OK 1 건 | 테스트 지도 관련 지도함.`

- [ ] **Step 6: 커밋**

```bash
git add src/teacher_widgets/widgets/counseling.py src/teacher_widgets/main.py tests/test_counseling.py tests/test_tray.py
git commit -m "feat: 상담기록 위젯(입력·역순 목록·복사·삭제·Excel)과 런처 등록

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 자기 점검 (Self-Review)

**1. Spec 커버리지:** 3요소(ts 자동·raw·refined)→T1 / 정제 규칙 4단계·빈 입력 거부(§3)→T1 / counseling.json + data_local(.bak)(§2)→T2 / 입력줄 Enter·역순 목록·툴팁·건수(§4)→T2 / 정제본 복사·삭제(확인 훅)(§4)→T2 / Excel 헤더·역순·열너비(§5)→T1·T2 / 등록(§6)→T2 / 축약 60자(§8)→T1 summary_line / 수정 불가·삭제만(§2·§9)→구조상(수정 API 없음) ✅
**2. 플레이스홀더:** 없음 ✅
**3. 타입 일관성:** `add_entry(data,raw,now=None)->dict|None`, `delete_entry(data,ts)->bool`, `sorted_entries(data)->list`, `summary_line(entry,limit=60)->str`, `build_counseling_workbook(entries)->Workbook`, `submit_text()->bool`, `delete_selected(ts)` — Task 간 일치. 테스트의 `item.data(32)`=Qt.UserRole ✅
