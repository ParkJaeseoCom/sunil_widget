# Phase 2 체크 위젯 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 번호별 체크박스로 숙제·제출 등을 점검하는 로컬 체크 위젯을 만들고, 출결 위젯과 공유할 학급 구성(남 N·여 M) 설정을 도입한다.

**Architecture:** 순수 로직(번호 생성, 체크 상태 헬퍼)은 PySide6 없이 테스트한다. `ChecklistWidget`은 기존 `BaseWidget`을 상속해 이동·리사이즈·저장·숨기기를 자동으로 얻고, 컨텍스트 메뉴 확장 훅으로 "제목 변경 / 학급 구성 설정 / 초기화"를 더한다. 다중 인스턴스는 Phase 1 메모와 동일한 고정 풀(checklist, checklist_1..3)로 트레이에서 on/off 한다.

**Tech Stack:** Python 3.14, PySide6 (Qt6 Widgets), pytest + pytest-qt, 기존 `teacher_widgets` 패키지.

## Global Constraints

- Python 3.14.x. PySide6 (Qt6 Widgets), QML 사용 안 함.
- 모든 테스트는 `QT_QPA_PLATFORM=offscreen` 에서 헤드리스로 통과해야 한다. 실행: `.venv/Scripts/python.exe -m pytest -v` (경로에 공백·한글 → 항상 따옴표).
- 패키지 루트 `src/teacher_widgets/`. import 경로 `teacher_widgets.core.*`, `teacher_widgets.widgets.*`.
- 번호 규칙: 남 = `1 .. boys`, 여 = `51 .. 50+girls`. 기본 학급 구성 `boys=14, girls=14`.
- 체크 상태는 `config.json`의 `checklists[name] = {"title": str, "checked": [int,...]}`. 학급 구성은 최상위 `class_roster = {"boys": int, "girls": int}`.
- 위젯 식별자: `checklist`, `checklist_1`, `checklist_2`, `checklist_3` (snake_case). 다중 인스턴스 고정 풀 4개.
- geometry는 `[x, y, w, h]` 정수. ConfigStore 공개 API: `data`, `load`, `save`, `get_widget`, `set_widget_visible`, `set_widget_geometry`, `get_opacity`, `set_opacity`.
- BaseWidget 공개 멤버: `__init__(widget_name, store)`, `content_layout`, `BASE_SIZE`, `restore_geometry`, `persist_geometry`, `hide_to_config`, `apply_opacity`, `set_locked`, `on_resized(w,h)`.
- 커밋 footer: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- 기존 49개 테스트를 깨뜨리지 말 것.

---

## 파일 구조

```
src/teacher_widgets/
├─ core/
│  ├─ roster.py            # (신규) roster_numbers 순수 함수
│  ├─ config_store.py      # (수정) class_roster 기본값 + get_roster/set_roster
│  └─ base_widget.py       # (수정) 컨텍스트 메뉴 확장 훅 _custom_menu_actions
├─ widgets/
│  └─ checklist.py         # (신규) 상태 헬퍼 + RosterDialog + TitleDialog + ChecklistWidget
├─ tray.py                 # (변경 없음 — 풀 등록은 main에서)
└─ main.py                 # (수정) checklist 풀 4개 등록
tests/
├─ test_roster.py          # (신규)
├─ test_config_store.py    # (수정) roster 테스트 추가
├─ test_base_widget.py     # (수정) 메뉴 훅 테스트 추가
├─ test_checklist.py       # (신규)
└─ test_tray.py            # (수정) checklist 등록 확인
```

---

## Task 1: 번호 생성 순수 함수 (roster)

**Files:**
- Create: `src/teacher_widgets/core/roster.py`
- Test: `tests/test_roster.py`

**Interfaces:**
- Consumes: (없음)
- Produces: `roster_numbers(boys: int, girls: int) -> list[int]` — `[1..boys]` 다음 `[51..50+girls]`.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_roster.py`:
```python
from teacher_widgets.core.roster import roster_numbers


def test_roster_numbers_boys_then_girls():
    assert roster_numbers(3, 2) == [1, 2, 3, 51, 52]


def test_roster_numbers_default_class():
    nums = roster_numbers(14, 14)
    assert nums[:14] == list(range(1, 15))
    assert nums[14:] == list(range(51, 65))
    assert len(nums) == 28


def test_roster_numbers_zero_sides():
    assert roster_numbers(0, 3) == [51, 52, 53]
    assert roster_numbers(2, 0) == [1, 2]
    assert roster_numbers(0, 0) == []
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `.venv/Scripts/python.exe -m pytest tests/test_roster.py -v`
Expected: FAIL (ModuleNotFoundError: teacher_widgets.core.roster)

- [ ] **Step 3: 최소 구현 작성**

`src/teacher_widgets/core/roster.py`:
```python
"""학급 번호 생성: 남 1부터, 여 51부터."""

from __future__ import annotations


def roster_numbers(boys: int, girls: int) -> list[int]:
    """남 [1..boys] 다음 여 [51..50+girls] 순서의 번호 목록."""
    boys = max(0, int(boys))
    girls = max(0, int(girls))
    return list(range(1, boys + 1)) + list(range(51, 51 + girls))
```

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `.venv/Scripts/python.exe -m pytest tests/test_roster.py -v`
Expected: 3 passed

- [ ] **Step 5: 커밋**

```bash
git add src/teacher_widgets/core/roster.py tests/test_roster.py
git commit -m "feat: 학급 번호 생성 순수 함수(roster_numbers) 구현

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: ConfigStore에 학급 구성 추가

**Files:**
- Modify: `src/teacher_widgets/core/config_store.py`
- Test: `tests/test_config_store.py`

**Interfaces:**
- Consumes: 기존 `ConfigStore`, `DEFAULT_CONFIG`, `deep_merge`.
- Produces:
  - `DEFAULT_CONFIG["class_roster"] = {"boys": 14, "girls": 14}`
  - `ConfigStore.get_roster() -> tuple[int, int]` (boys, girls)
  - `ConfigStore.set_roster(boys: int, girls: int) -> None` (값 저장; save는 호출하지 않음 — 호출측 책임, 기존 set_* 들과 동일 관례)

- [ ] **Step 1: 실패하는 테스트 작성 (기존 test_config_store.py 끝에 추가)**

```python
def test_default_roster(tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    assert store.get_roster() == (14, 14)


def test_set_roster_roundtrip(tmp_path):
    path = tmp_path / "config.json"
    store = ConfigStore(path)
    store.load()
    store.set_roster(10, 12)
    assert store.get_roster() == (10, 12)
    store.save()

    reloaded = ConfigStore(path)
    reloaded.load()
    assert reloaded.get_roster() == (10, 12)
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `.venv/Scripts/python.exe -m pytest tests/test_config_store.py -k roster -v`
Expected: FAIL (AttributeError: 'ConfigStore' object has no attribute 'get_roster')

- [ ] **Step 3: 구현 — DEFAULT_CONFIG에 키 추가 + 메서드 2개**

`config_store.py`의 `DEFAULT_CONFIG`에 `class_roster` 항목 추가:
```python
DEFAULT_CONFIG: dict = {
    "theme": "pastel",
    "widget_opacity": 96,
    "layout_locked": False,
    "class_roster": {"boys": 14, "girls": 14},
    "widgets": {},
}
```

`ConfigStore` 클래스에 메서드 추가 (set_opacity 아래 등 적당한 위치):
```python
    def get_roster(self) -> tuple[int, int]:
        roster = self.data["class_roster"]
        return int(roster["boys"]), int(roster["girls"])

    def set_roster(self, boys: int, girls: int) -> None:
        self.data["class_roster"] = {"boys": int(boys), "girls": int(girls)}
```

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `.venv/Scripts/python.exe -m pytest tests/test_config_store.py -v`
Expected: 모든 config_store 테스트 통과(기존 + 신규 2). `deep_merge`가 `DEFAULT_CONFIG`를 기준으로 병합하므로 구버전 config(키 없음) 로드 시에도 기본 roster가 채워진다.

- [ ] **Step 5: 커밋**

```bash
git add src/teacher_widgets/core/config_store.py tests/test_config_store.py
git commit -m "feat: ConfigStore에 공유 학급 구성(class_roster) 추가

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: BaseWidget 컨텍스트 메뉴 확장 훅

**Files:**
- Modify: `src/teacher_widgets/core/base_widget.py`
- Test: `tests/test_base_widget.py`

**Interfaces:**
- Consumes: 기존 `BaseWidget._show_menu`.
- Produces: `BaseWidget._custom_menu_actions(self, menu: QtWidgets.QMenu) -> dict` — 기본 `{}`. 서브클래스가 오버라이드해 `{action: callable}`를 반환하면 잠금/닫기 위에 표시되고, 선택 시 해당 callable이 호출된다.

- [ ] **Step 1: 실패하는 테스트 작성 (test_base_widget.py에 추가)**

```python
def test_custom_menu_actions_default_empty(qtbot, tmp_path):
    store = make_store(tmp_path)
    w = BaseWidget("clock", store)
    qtbot.addWidget(w)
    menu = QtWidgets.QMenu()
    assert w._custom_menu_actions(menu) == {}


def test_custom_menu_actions_subclass_callback_invoked(qtbot, tmp_path):
    store = make_store(tmp_path)
    calls = []

    class Sub(BaseWidget):
        def _custom_menu_actions(self, menu):
            act = menu.addAction("테스트 동작")
            return {act: lambda: calls.append("ran")}

    w = Sub("clock", store)
    qtbot.addWidget(w)
    menu = QtWidgets.QMenu()
    custom = w._custom_menu_actions(menu)
    assert len(custom) == 1
    # 콜백 직접 실행으로 배선 검증
    list(custom.values())[0]()
    assert calls == ["ran"]
```

(`test_base_widget.py` 상단에 `from PySide6 import QtWidgets` 가 없으면 추가. 기존 import 확인 후 필요 시 보강.)

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `.venv/Scripts/python.exe -m pytest tests/test_base_widget.py -k custom_menu -v`
Expected: FAIL (AttributeError: 'BaseWidget' object has no attribute '_custom_menu_actions')

- [ ] **Step 3: 구현 — 훅 추가 + _show_menu 배선**

`base_widget.py`에 메서드 추가 (`_show_menu` 바로 위):
```python
    def _custom_menu_actions(self, menu: QtWidgets.QMenu) -> dict:
        """서브클래스가 컨텍스트 메뉴에 항목을 추가하는 훅.

        {QAction: callable} 을 반환하면 잠금/닫기 위에 표시되고
        선택 시 해당 callable 이 호출된다. 기본은 항목 없음.
        """
        return {}
```

`_show_menu`를 다음으로 교체:
```python
    def _show_menu(self, pos: QtCore.QPoint) -> None:
        menu = QtWidgets.QMenu(self)
        custom = self._custom_menu_actions(menu)
        if custom:
            menu.addSeparator()
        lock_action = menu.addAction("이동 잠금 해제" if self._locked else "이동 잠금")
        close_action = menu.addAction("이 위젯 닫기")
        chosen = menu.exec(self.mapToGlobal(pos))
        if chosen is None:
            return
        if chosen in custom:
            custom[chosen]()
        elif chosen == lock_action:
            self.set_locked(not self._locked)
        elif chosen == close_action:
            self.hide_to_config()
```

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `.venv/Scripts/python.exe -m pytest tests/test_base_widget.py -v`
Expected: 기존 base_widget 테스트 + 신규 2 모두 통과.

- [ ] **Step 5: 커밋**

```bash
git add src/teacher_widgets/core/base_widget.py tests/test_base_widget.py
git commit -m "feat: BaseWidget 컨텍스트 메뉴 확장 훅 추가

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: 체크 상태 헬퍼 함수

**Files:**
- Create: `src/teacher_widgets/widgets/checklist.py` (헬퍼 부분만 — 위젯은 Task 6)
- Test: `tests/test_checklist.py`

**Interfaces:**
- Consumes: `ConfigStore` (`.data`, `.save`).
- Produces (모듈 함수):
  - `get_title(store, name: str) -> str` (기본 "체크")
  - `set_title(store, name: str, title: str) -> None` (save 호출)
  - `get_checked(store, name: str) -> set[int]`
  - `set_checked(store, name: str, numbers: set[int]) -> None` (정렬된 list로 저장 + save)
  - `toggle(store, name: str, number: int) -> bool` (번호 체크 토글, 토글 후 체크 상태 반환, save)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_checklist.py`:
```python
from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.widgets.checklist import (
    get_title,
    set_title,
    get_checked,
    set_checked,
    toggle,
)


def make_store(tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    return store


def test_title_default_and_roundtrip(tmp_path):
    store = make_store(tmp_path)
    assert get_title(store, "checklist") == "체크"
    set_title(store, "checklist", "숙제 검사")
    assert get_title(store, "checklist") == "숙제 검사"


def test_checked_roundtrip_sorted(tmp_path):
    store = make_store(tmp_path)
    assert get_checked(store, "checklist") == set()
    set_checked(store, "checklist", {7, 3, 51})
    assert get_checked(store, "checklist") == {3, 7, 51}
    # 저장은 정렬된 list
    assert store.data["checklists"]["checklist"]["checked"] == [3, 7, 51]


def test_toggle_adds_then_removes(tmp_path):
    store = make_store(tmp_path)
    assert toggle(store, "checklist", 5) is True
    assert get_checked(store, "checklist") == {5}
    assert toggle(store, "checklist", 5) is False
    assert get_checked(store, "checklist") == set()


def test_instances_are_independent(tmp_path):
    store = make_store(tmp_path)
    set_checked(store, "checklist", {1})
    set_checked(store, "checklist_1", {51})
    assert get_checked(store, "checklist") == {1}
    assert get_checked(store, "checklist_1") == {51}
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `.venv/Scripts/python.exe -m pytest tests/test_checklist.py -v`
Expected: FAIL (ModuleNotFoundError: teacher_widgets.widgets.checklist)

- [ ] **Step 3: 최소 구현 작성 (헬퍼만)**

`src/teacher_widgets/widgets/checklist.py`:
```python
"""체크 위젯: 상태 헬퍼 + 다이얼로그 + ChecklistWidget.

이 파일의 상단부(헬퍼 함수)는 Task 4, 다이얼로그·위젯은 Task 6에서 추가된다.
"""

from __future__ import annotations

from teacher_widgets.core.config_store import ConfigStore

_DEFAULT_TITLE = "체크"


def _slot(store: ConfigStore, name: str) -> dict:
    checklists = store.data.setdefault("checklists", {})
    return checklists.setdefault(name, {"title": _DEFAULT_TITLE, "checked": []})


def get_title(store: ConfigStore, name: str) -> str:
    return _slot(store, name).get("title", _DEFAULT_TITLE)


def set_title(store: ConfigStore, name: str, title: str) -> None:
    _slot(store, name)["title"] = title
    store.save()


def get_checked(store: ConfigStore, name: str) -> set[int]:
    return {int(n) for n in _slot(store, name).get("checked", [])}


def set_checked(store: ConfigStore, name: str, numbers: set[int]) -> None:
    _slot(store, name)["checked"] = sorted(int(n) for n in numbers)
    store.save()


def toggle(store: ConfigStore, name: str, number: int) -> bool:
    checked = get_checked(store, name)
    if number in checked:
        checked.discard(number)
        result = False
    else:
        checked.add(number)
        result = True
    set_checked(store, name, checked)
    return result
```

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `.venv/Scripts/python.exe -m pytest tests/test_checklist.py -v`
Expected: 4 passed

- [ ] **Step 5: 커밋**

```bash
git add src/teacher_widgets/widgets/checklist.py tests/test_checklist.py
git commit -m "feat: 체크 상태 헬퍼(title/checked/toggle) 구현

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: 학급 구성 다이얼로그 + 제목 다이얼로그

**Files:**
- Modify: `src/teacher_widgets/widgets/checklist.py` (다이얼로그 추가)
- Test: `tests/test_checklist.py` (다이얼로그 테스트 추가)

**Interfaces:**
- Consumes: PySide6.
- Produces:
  - `class RosterDialog(QtWidgets.QDialog)` — `__init__(boys: int, girls: int, parent=None)`; 스핀박스 2개(남/여, 범위 0~30); `values() -> tuple[int, int]`.
  - `class TitleDialog(QtWidgets.QDialog)` — `__init__(title: str, parent=None)`; 한 줄 입력; `value() -> str`.

- [ ] **Step 1: 실패하는 테스트 작성 (test_checklist.py에 추가)**

```python
from PySide6 import QtWidgets  # 파일 상단에 없으면 추가
from teacher_widgets.widgets.checklist import RosterDialog, TitleDialog


def test_roster_dialog_returns_values(qtbot):
    dlg = RosterDialog(10, 12)
    qtbot.addWidget(dlg)
    assert dlg.values() == (10, 12)
    dlg.boys_spin.setValue(8)
    dlg.girls_spin.setValue(9)
    assert dlg.values() == (8, 9)


def test_roster_dialog_clamps_range(qtbot):
    dlg = RosterDialog(0, 0)
    qtbot.addWidget(dlg)
    dlg.boys_spin.setValue(999)  # 최대 30으로 클램프
    assert dlg.values()[0] == 30


def test_title_dialog_returns_value(qtbot):
    dlg = TitleDialog("숙제")
    qtbot.addWidget(dlg)
    assert dlg.value() == "숙제"
    dlg.edit.setText("우유 확인")
    assert dlg.value() == "우유 확인"
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `.venv/Scripts/python.exe -m pytest tests/test_checklist.py -k dialog -v`
Expected: FAIL (ImportError: cannot import name 'RosterDialog')

- [ ] **Step 3: 구현 — checklist.py에 다이얼로그 추가**

`checklist.py` 상단 import에 PySide6 추가:
```python
from PySide6 import QtWidgets
```

파일에 클래스 추가:
```python
class RosterDialog(QtWidgets.QDialog):
    def __init__(self, boys: int, girls: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("학급 구성 설정")
        form = QtWidgets.QFormLayout(self)

        self.boys_spin = QtWidgets.QSpinBox()
        self.boys_spin.setRange(0, 30)
        self.boys_spin.setValue(int(boys))
        self.girls_spin = QtWidgets.QSpinBox()
        self.girls_spin.setRange(0, 30)
        self.girls_spin.setValue(int(girls))

        form.addRow("남학생 수", self.boys_spin)
        form.addRow("여학생 수", self.girls_spin)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self) -> tuple[int, int]:
        return self.boys_spin.value(), self.girls_spin.value()


class TitleDialog(QtWidgets.QDialog):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("제목 변경")
        layout = QtWidgets.QVBoxLayout(self)
        self.edit = QtWidgets.QLineEdit(title)
        layout.addWidget(self.edit)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def value(self) -> str:
        return self.edit.text()
```

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `.venv/Scripts/python.exe -m pytest tests/test_checklist.py -v`
Expected: 헬퍼 4 + 다이얼로그 3 = 모두 통과.

- [ ] **Step 5: 커밋**

```bash
git add src/teacher_widgets/widgets/checklist.py tests/test_checklist.py
git commit -m "feat: 학급 구성/제목 변경 다이얼로그 구현

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: ChecklistWidget (GUI)

**Files:**
- Modify: `src/teacher_widgets/widgets/checklist.py` (ChecklistWidget 추가)
- Test: `tests/test_checklist.py` (위젯 테스트 추가)

**Interfaces:**
- Consumes: `BaseWidget`, `ConfigStore`, `roster_numbers` (Task 1), 헬퍼(Task 4), 다이얼로그(Task 5), `_custom_menu_actions` 훅(Task 3), `responsive.scale_factor/scaled_font_pt`.
- Produces:
  - `class ChecklistWidget(BaseWidget)` — `__init__(self, store, name="checklist")`.
    - `rebuild_grid() -> None` (현재 roster로 번호 버튼 재생성)
    - `update_count() -> None` (제출 카운트 라벨 갱신)
    - `_on_toggle(number: int) -> None`
    - `reset() -> None` (모두 해제 + 갱신)
    - `change_title() -> None` / `change_roster() -> None` (다이얼로그 → 저장 → 갱신)
    - 속성: `title_label`, `count_label`, `grid_container`, `_buttons: dict[int, QToolButton]`

- [ ] **Step 1: 실패하는 테스트 작성 (test_checklist.py에 추가)**

```python
from teacher_widgets.widgets.checklist import ChecklistWidget


def test_widget_builds_grid_from_roster(qtbot, tmp_path):
    store = make_store(tmp_path)
    store.set_roster(3, 2)  # 1,2,3,51,52
    w = ChecklistWidget(store, "checklist")
    qtbot.addWidget(w)
    assert sorted(w._buttons.keys()) == [1, 2, 3, 51, 52]


def test_widget_toggle_updates_count_and_config(qtbot, tmp_path):
    store = make_store(tmp_path)
    store.set_roster(3, 0)
    w = ChecklistWidget(store, "checklist")
    qtbot.addWidget(w)
    assert "0/3" in w.count_label.text()
    w._on_toggle(2)
    assert "1/3" in w.count_label.text()
    assert 2 in store.data["checklists"]["checklist"]["checked"]


def test_widget_reset_clears_all(qtbot, tmp_path):
    store = make_store(tmp_path)
    store.set_roster(3, 0)
    w = ChecklistWidget(store, "checklist")
    qtbot.addWidget(w)
    w._on_toggle(1)
    w._on_toggle(2)
    w.reset()
    assert "0/3" in w.count_label.text()
    assert store.data["checklists"]["checklist"]["checked"] == []


def test_widget_title_from_config(qtbot, tmp_path):
    store = make_store(tmp_path)
    set_title(store, "checklist", "숙제 검사")
    w = ChecklistWidget(store, "checklist")
    qtbot.addWidget(w)
    assert w.title_label.text() == "숙제 검사"


def test_widget_change_roster_rebuilds_grid(qtbot, tmp_path):
    store = make_store(tmp_path)
    store.set_roster(2, 0)
    w = ChecklistWidget(store, "checklist")
    qtbot.addWidget(w)
    assert sorted(w._buttons.keys()) == [1, 2]
    # roster 변경을 직접 적용(다이얼로그 우회)
    store.set_roster(2, 1)
    store.save()
    w.rebuild_grid()
    assert sorted(w._buttons.keys()) == [1, 2, 51]


def test_widget_name_passed_to_base(qtbot, tmp_path):
    store = make_store(tmp_path)
    w = ChecklistWidget(store, "checklist_2")
    qtbot.addWidget(w)
    assert w.widget_name == "checklist_2"
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `.venv/Scripts/python.exe -m pytest tests/test_checklist.py -k widget -v`
Expected: FAIL (ImportError: cannot import name 'ChecklistWidget')

- [ ] **Step 3: 구현 — ChecklistWidget 추가**

`checklist.py` import 보강:
```python
from PySide6 import QtCore, QtGui, QtWidgets

from teacher_widgets.core.base_widget import BaseWidget
from teacher_widgets.core.roster import roster_numbers
from teacher_widgets.core.responsive import scale_factor, scaled_font_pt
```

클래스 추가:
```python
class ChecklistWidget(BaseWidget):
    BASE_SIZE = (240, 320)

    def __init__(self, store: ConfigStore, name: str = "checklist"):
        super().__init__(name, store)
        self._buttons: dict[int, QtWidgets.QToolButton] = {}

        self.title_label = QtWidgets.QLabel(get_title(store, name))
        self.title_label.setAlignment(QtCore.Qt.AlignCenter)
        self.title_label.setStyleSheet("font-weight:700; color:#2b2b2b;")

        self.count_label = QtWidgets.QLabel("")
        self.count_label.setAlignment(QtCore.Qt.AlignCenter)
        self.count_label.setStyleSheet("color:#666;")

        self.grid_container = QtWidgets.QWidget()
        self.grid_layout = QtWidgets.QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        reset_btn = QtWidgets.QPushButton("초기화")
        reset_btn.clicked.connect(self.reset)

        self.content_layout.addWidget(self.title_label)
        self.content_layout.addWidget(self.count_label)
        self.content_layout.addWidget(self.grid_container)
        self.content_layout.addStretch(1)
        self.content_layout.addWidget(reset_btn)

        self.rebuild_grid()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(QtGui.QColor(255, 255, 255, 235))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 16, 16)

    # --- 그리드 ---
    def rebuild_grid(self) -> None:
        for btn in self._buttons.values():
            btn.deleteLater()
        self._buttons.clear()
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        boys, girls = self.store.get_roster()
        checked = get_checked(self.store, self.widget_name)
        numbers = roster_numbers(boys, girls)
        cols = 3
        for idx, num in enumerate(numbers):
            btn = QtWidgets.QToolButton()
            btn.setCheckable(True)
            btn.setText(str(num))
            btn.setChecked(num in checked)
            btn.clicked.connect(lambda _checked, n=num: self._on_toggle(n))
            self._buttons[num] = btn
            self.grid_layout.addWidget(btn, idx // cols, idx % cols)
        self.update_count()
        self._apply_responsive()

    def update_count(self) -> None:
        boys, girls = self.store.get_roster()
        total = boys + girls
        done = len(get_checked(self.store, self.widget_name))
        self.count_label.setText(f"제출 {done}/{total}")

    def _on_toggle(self, number: int) -> None:
        toggle(self.store, self.widget_name, number)
        self.update_count()

    def reset(self) -> None:
        set_checked(self.store, self.widget_name, set())
        for btn in self._buttons.values():
            btn.setChecked(False)
        self.update_count()

    # --- 메뉴 / 다이얼로그 ---
    def _custom_menu_actions(self, menu) -> dict:
        title_action = menu.addAction("제목 변경")
        roster_action = menu.addAction("학급 구성 설정")
        reset_action = menu.addAction("초기화")
        return {
            title_action: self.change_title,
            roster_action: self.change_roster,
            reset_action: self.reset,
        }

    def change_title(self) -> None:
        dlg = TitleDialog(get_title(self.store, self.widget_name), self)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            set_title(self.store, self.widget_name, dlg.value())
            self.title_label.setText(dlg.value())

    def change_roster(self) -> None:
        boys, girls = self.store.get_roster()
        dlg = RosterDialog(boys, girls, self)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            new_boys, new_girls = dlg.values()
            self.store.set_roster(new_boys, new_girls)
            self.store.save()
            self.rebuild_grid()

    # --- 반응형 ---
    def _apply_responsive(self) -> None:
        factor = scale_factor((self.width(), self.height()), self.BASE_SIZE)
        self.title_label.setStyleSheet(
            f"font-weight:700; color:#2b2b2b; font-size:{scaled_font_pt(13, factor)}pt;"
        )
        self.count_label.setStyleSheet(
            f"color:#666; font-size:{scaled_font_pt(10, factor)}pt;"
        )

    def on_resized(self, width: int, height: int) -> None:
        self._apply_responsive()
```

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `.venv/Scripts/python.exe -m pytest tests/test_checklist.py -v`
Expected: 헬퍼 4 + 다이얼로그 3 + 위젯 6 = 모두 통과.

- [ ] **Step 5: 전체 스위트 확인 후 커밋**

Run: `.venv/Scripts/python.exe -m pytest -v` → 전부 green.
```bash
git add src/teacher_widgets/widgets/checklist.py tests/test_checklist.py
git commit -m "feat: 체크 위젯(번호 그리드·카운트·초기화·메뉴) 구현

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: 런처에 체크 풀 등록

**Files:**
- Modify: `src/teacher_widgets/main.py`
- Test: `tests/test_tray.py`

**Interfaces:**
- Consumes: `ChecklistWidget` (Task 6), `WidgetRegistry`.
- Produces: main에서 `checklist`, `checklist_1`, `checklist_2`, `checklist_3` 4개 인스턴스를 등록. 최초 실행 기본은 기존대로 `clock`만 표시(체크는 사용자가 트레이에서 켬).

- [ ] **Step 1: 실패하는 테스트 작성 (test_tray.py에 추가)**

```python
from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.core.base_widget import BaseWidget
from teacher_widgets.core.registry import WidgetRegistry
from teacher_widgets.tray import build_tray_menu


def test_tray_menu_lists_checklist_pool(qtbot, tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    reg = WidgetRegistry(store)
    for nm in ("checklist", "checklist_1", "checklist_2", "checklist_3"):
        reg.register(nm, lambda nm=nm: BaseWidget(nm, store))
    menu = build_tray_menu(reg)
    texts = [a.text() for a in menu.actions() if a.text()]
    for nm in ("checklist", "checklist_1", "checklist_2", "checklist_3"):
        assert nm in texts
```

(이 테스트는 tray가 등록된 이름을 메뉴에 노출하는지를 BaseWidget 스텁으로 검증한다 — main 의존 없이.)

- [ ] **Step 2: 테스트 실행하여 통과 확인 (tray는 이미 일반적이라 바로 통과해야 함)**

Run: `.venv/Scripts/python.exe -m pytest tests/test_tray.py -v`
Expected: 신규 포함 모두 통과. (만약 실패하면 tray.build_tray_menu가 names() 순회를 하는지 점검)

- [ ] **Step 3: main.py에 체크 풀 등록**

`main.py`의 import에 추가:
```python
from .widgets.checklist import ChecklistWidget
```

`registry.register("memo", ...)` 다음 줄들에 추가:
```python
    for nm in ("checklist", "checklist_1", "checklist_2", "checklist_3"):
        registry.register(nm, lambda store=store, nm=nm: ChecklistWidget(store, nm))
```

- [ ] **Step 4: 비차단 구성 스모크 체크**

Run (비차단 — app.exec 진입 금지):
```bash
.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'src'); from PySide6 import QtWidgets; app=QtWidgets.QApplication([]); from teacher_widgets.core.config_store import ConfigStore; from teacher_widgets.core.registry import WidgetRegistry; from teacher_widgets.widgets.checklist import ChecklistWidget; import tempfile,os; d=tempfile.mkdtemp(); s=ConfigStore(os.path.join(d,'c.json')); s.load(); r=WidgetRegistry(s); [r.register(n, (lambda s=s,n=n: ChecklistWidget(s,n))) for n in ('checklist','checklist_1')]; w=r.show('checklist'); print('OK', w.widget_name, sorted(w._buttons.keys())[:3])"
```
Expected: `OK checklist [1, 2, 3]` 류 출력, 예외 없음. (offscreen 환경 변수 필요 시 `QT_QPA_PLATFORM=offscreen` 앞에 설정)

- [ ] **Step 5: 전체 스위트 + 커밋**

Run: `.venv/Scripts/python.exe -m pytest -v` → 전부 green.
```bash
git add src/teacher_widgets/main.py tests/test_tray.py
git commit -m "feat: 런처에 체크 위젯 풀(4개) 등록

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 자기 점검 (Self-Review)

**1. Spec 커버리지**
- 공유 학급 구성 class_roster + 번호규칙(남1~/여51~) → Task 1(roster_numbers) + Task 2(config) ✅
- 기본값 14/14 → Task 2 ✅
- 우클릭 "학급 구성 설정" 다이얼로그 → Task 5(RosterDialog) + Task 6(change_roster) + Task 3(메뉴 훅) ✅
- 이진 체크 + 제출 카운트 + 초기화 → Task 6 ✅
- 제목 편집 → Task 5(TitleDialog) + Task 6(change_title) ✅
- 다중 인스턴스 고정 풀(checklist_0..3) → Task 7 ✅
- 데이터 모델(class_roster, checklists[name]) → Task 2 + Task 4 ✅
- 반응형·공통(BaseWidget) → Task 6 on_resized ✅
- 엣지: 인원 축소 후 그리드는 유효 번호만(rebuild_grid가 roster_numbers로 재생성, checked 데이터는 보존) → Task 6 ✅
- 인스턴스 독립성 테스트 → Task 4 ✅

**2. 플레이스홀더 스캔:** "TBD/적절히" 없음. 모든 코드 스텝에 실제 코드 포함 ✅

**3. 타입 일관성:** `get_roster()->tuple[int,int]`, `roster_numbers(boys,girls)->list[int]`, `get_checked->set[int]`, `set_checked(...,set[int])`, `toggle(...)->bool`, `_custom_menu_actions(menu)->dict`, `ChecklistWidget(store, name)` — Task 간 시그니처 일치 ✅

**미해결(범위 밖):** 시간표 위젯(Firestore), 동적 무제한 추가, 학급 구성 전역 설정 UI — 후속.
