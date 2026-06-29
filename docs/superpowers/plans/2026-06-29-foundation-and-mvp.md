# Phase 0 기반 + Phase 1 MVP 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 교사용 데스크톱 위젯의 공통 기반(설정 저장·반응형·프레임리스 베이스·트레이 런처·exe 배포)을 만들고, 그 위에 시계·타이머·메모 3종 위젯을 올려 첫 배포 가능한 상태를 만든다.

**Architecture:** 순수 로직(설정 저장·반응형 계산·타이머 모델·시간 포맷)은 PySide6에 의존하지 않는 테스트 가능한 모듈로 분리한다. GUI는 그 위에 얇게 얹는다. 모든 위젯은 `BaseWidget`을 상속해 프레임리스·반투명·이동·리사이즈·위치저장·숨기기를 자동으로 얻는다. 상태는 단일 `config.json`에 저장한다.

**Tech Stack:** Python 3.14, PySide6 (Qt Widgets), pytest + pytest-qt, PyInstaller.

## Global Constraints

- Python 버전: 3.14.x (개발 PC 설치본 3.14.6).
- GUI 프레임워크: PySide6 (Qt6 Widgets). QML 사용 안 함.
- 모든 테스트는 `QT_QPA_PLATFORM=offscreen` 환경에서 GUI 없이 실행 가능해야 한다.
- 패키지 루트: `src/teacher_widgets/`. 임포트 경로 `teacher_widgets.core.*`, `teacher_widgets.widgets.*`.
- 설정 파일 경로: 실행 파일 기준 `teacher-widgets-data/config.json` (레퍼런스와 동일 폴더명). 테스트에서는 임시 경로 주입.
- 위젯 식별자(widget_name)는 영문 소문자 스네이크 케이스: `clock`, `timer`, `memo`, `memo_1` 등.
- 좌표 표기: geometry는 `[x, y, w, h]` 정수 리스트(레퍼런스 config 형식 계승).
- 커밋 메시지 말미에 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` 포함.

---

## 파일 구조

```
위젯/
├─ pyproject.toml                      # 패키지/의존성/pytest 설정
├─ src/teacher_widgets/
│  ├─ __init__.py
│  ├─ core/
│  │  ├─ __init__.py
│  │  ├─ config_store.py               # config.json 로드/세이브, 기본값, 위젯 상태 접근
│  │  ├─ responsive.py                 # 크기→스케일/폰트, 내용 구간(breakpoint)
│  │  ├─ base_widget.py                # 프레임리스·반투명·이동·리사이즈·위치저장·숨기기
│  │  └─ registry.py                   # 위젯 등록/표시/숨김 컨트롤러(트레이와 분리)
│  ├─ widgets/
│  │  ├─ __init__.py
│  │  ├─ clock.py                      # 시간 포맷 순수함수 + ClockWidget
│  │  ├─ timer.py                      # TimerModel 순수클래스 + TimerWidget
│  │  └─ memo.py                       # 메모 저장 헬퍼 + MemoWidget
│  ├─ tray.py                          # QSystemTrayIcon 런처(UI)
│  └─ main.py                          # 진입점: 설정 로드 → 등록 → 복원 → 트레이 → 실행
├─ tests/
│  ├─ conftest.py                      # offscreen 설정 + qapp/qtbot 픽스처
│  ├─ test_config_store.py
│  ├─ test_responsive.py
│  ├─ test_base_widget.py
│  ├─ test_registry.py
│  ├─ test_clock.py
│  ├─ test_timer.py
│  └─ test_memo.py
├─ build/
│  ├─ teacher_widgets.spec             # PyInstaller 스펙
│  ├─ install_startup.bat              # 시작프로그램 등록(레퍼런스 계승)
│  └─ uninstall_startup.bat            # 시작프로그램 해제
└─ assets/
   └─ icon.png                         # 트레이 아이콘(임시)
```

---

## Task 1: 프로젝트 골격 & 개발 환경

**Files:**
- Create: `pyproject.toml`
- Create: `src/teacher_widgets/__init__.py`
- Create: `src/teacher_widgets/core/__init__.py`
- Create: `src/teacher_widgets/widgets/__init__.py`
- Create: `tests/conftest.py`
- Test: `tests/test_smoke.py`

**Interfaces:**
- Consumes: (없음)
- Produces: 임포트 가능한 `teacher_widgets` 패키지, `conftest.py`의 `qtbot` 픽스처(pytest-qt 제공), offscreen 환경.

- [ ] **Step 1: 가상환경 생성 및 의존성 설치**

```bash
cd "위젯"
py -3.14 -m venv .venv
source .venv/Scripts/activate   # Git Bash 기준. PowerShell은 .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install PySide6 pytest pytest-qt pyinstaller
pip freeze > requirements.txt
```

Expected: PySide6, pytest, pytest-qt, pyinstaller 설치 성공.

- [ ] **Step 2: pyproject.toml 작성**

```toml
[project]
name = "teacher-widgets"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = ["PySide6"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v"
```

- [ ] **Step 3: 패키지 초기 파일 생성**

`src/teacher_widgets/__init__.py`:
```python
"""교사용 데스크톱 위젯 모음."""

__version__ = "0.1.0"
```

`src/teacher_widgets/core/__init__.py`:
```python
```

`src/teacher_widgets/widgets/__init__.py`:
```python
```

- [ ] **Step 4: conftest.py 작성 (offscreen + 경로)**

`tests/conftest.py`:
```python
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))
```

- [ ] **Step 5: 스모크 테스트 작성**

`tests/test_smoke.py`:
```python
def test_package_imports():
    import teacher_widgets

    assert teacher_widgets.__version__ == "0.1.0"


def test_pyside6_available():
    from PySide6 import QtWidgets

    assert QtWidgets is not None
```

- [ ] **Step 6: 테스트 실행하여 통과 확인**

Run: `python -m pytest tests/test_smoke.py -v`
Expected: 2 passed

- [ ] **Step 7: 커밋**

```bash
git add pyproject.toml requirements.txt src tests
git commit -m "chore: 프로젝트 골격과 개발 환경 구축

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: 설정 저장소 (config_store)

**Files:**
- Create: `src/teacher_widgets/core/config_store.py`
- Test: `tests/test_config_store.py`

**Interfaces:**
- Consumes: (없음)
- Produces:
  - `DEFAULT_CONFIG: dict`
  - `deep_merge(base: dict, override: dict) -> dict`
  - `class ConfigStore`
    - `__init__(self, path: pathlib.Path)`
    - `data: dict`
    - `load() -> dict`
    - `save() -> None`
    - `get_widget(name: str) -> dict`  → `{"visible": bool, "geometry": [x,y,w,h]}`
    - `set_widget_visible(name: str, visible: bool) -> None`
    - `set_widget_geometry(name: str, geometry: list[int]) -> None`
    - `get_opacity() -> int`
    - `set_opacity(percent: int) -> None`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_config_store.py`:
```python
import json
from pathlib import Path

from teacher_widgets.core.config_store import ConfigStore, deep_merge, DEFAULT_CONFIG


def test_deep_merge_overrides_nested():
    base = {"a": 1, "b": {"c": 2, "d": 3}}
    override = {"b": {"c": 99}}
    result = deep_merge(base, override)
    assert result == {"a": 1, "b": {"c": 99, "d": 3}}


def test_load_missing_file_returns_defaults(tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    data = store.load()
    assert data["widget_opacity"] == DEFAULT_CONFIG["widget_opacity"]


def test_save_then_reload_roundtrip(tmp_path):
    path = tmp_path / "config.json"
    store = ConfigStore(path)
    store.load()
    store.set_widget_visible("clock", False)
    store.set_widget_geometry("clock", [10, 20, 200, 120])
    store.save()

    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["widgets"]["clock"] == {"visible": False, "geometry": [10, 20, 200, 120]}


def test_get_widget_unknown_returns_default_geometry(tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    w = store.get_widget("memo_3")
    assert w["visible"] is True
    assert len(w["geometry"]) == 4


def test_opacity_get_set(tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    store.set_opacity(80)
    assert store.get_opacity() == 80
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `python -m pytest tests/test_config_store.py -v`
Expected: FAIL (ModuleNotFoundError: teacher_widgets.core.config_store)

- [ ] **Step 3: 최소 구현 작성**

`src/teacher_widgets/core/config_store.py`:
```python
"""단일 config.json 상태 저장소."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

DEFAULT_WIDGET = {"visible": True, "geometry": [100, 100, 220, 140]}

DEFAULT_CONFIG: dict = {
    "theme": "pastel",
    "widget_opacity": 96,
    "layout_locked": False,
    "widgets": {},
}


def deep_merge(base: dict, override: dict) -> dict:
    """override 값을 base 위에 재귀 병합한 새 dict 반환."""
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


class ConfigStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.data: dict = deepcopy(DEFAULT_CONFIG)

    def load(self) -> dict:
        if self.path.exists():
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self.data = deep_merge(DEFAULT_CONFIG, raw)
        else:
            self.data = deepcopy(DEFAULT_CONFIG)
        return self.data

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get_widget(self, name: str) -> dict:
        widget = self.data["widgets"].get(name)
        if widget is None:
            return deepcopy(DEFAULT_WIDGET)
        return deep_merge(DEFAULT_WIDGET, widget)

    def _widget_slot(self, name: str) -> dict:
        return self.data["widgets"].setdefault(name, deepcopy(DEFAULT_WIDGET))

    def set_widget_visible(self, name: str, visible: bool) -> None:
        self._widget_slot(name)["visible"] = bool(visible)

    def set_widget_geometry(self, name: str, geometry: list[int]) -> None:
        self._widget_slot(name)["geometry"] = [int(v) for v in geometry]

    def get_opacity(self) -> int:
        return int(self.data["widget_opacity"])

    def set_opacity(self, percent: int) -> None:
        self.data["widget_opacity"] = int(percent)
```

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `python -m pytest tests/test_config_store.py -v`
Expected: 5 passed

- [ ] **Step 5: 커밋**

```bash
git add src/teacher_widgets/core/config_store.py tests/test_config_store.py
git commit -m "feat: config.json 단일 상태 저장소 구현

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: 반응형 계산 (responsive)

**Files:**
- Create: `src/teacher_widgets/core/responsive.py`
- Test: `tests/test_responsive.py`

**Interfaces:**
- Consumes: (없음)
- Produces:
  - `scale_factor(current: tuple[int, int], base: tuple[int, int], min_factor=0.6, max_factor=3.0) -> float`
  - `scaled_font_pt(base_pt: float, factor: float, min_pt=8, max_pt=72) -> int`
  - `resolve_breakpoint(width: int, thresholds: list[tuple[int, str]]) -> str`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_responsive.py`:
```python
from teacher_widgets.core.responsive import (
    scale_factor,
    scaled_font_pt,
    resolve_breakpoint,
)


def test_scale_factor_uses_smaller_axis_ratio():
    # 폭은 2배, 높이는 1.5배 → 더 작은 1.5 채택(내용 잘림 방지)
    assert scale_factor((400, 300), (200, 200)) == 1.5


def test_scale_factor_clamped_to_min():
    assert scale_factor((10, 10), (200, 200), min_factor=0.6) == 0.6


def test_scale_factor_clamped_to_max():
    assert scale_factor((9999, 9999), (200, 200), max_factor=3.0) == 3.0


def test_scaled_font_pt_rounds_and_clamps():
    assert scaled_font_pt(12, 2.0) == 24
    assert scaled_font_pt(12, 0.1, min_pt=8) == 8
    assert scaled_font_pt(40, 2.0, max_pt=72) == 72


def test_resolve_breakpoint_picks_largest_threshold_not_exceeding_width():
    thresholds = [(0, "today"), (300, "today_tomorrow"), (520, "week")]
    assert resolve_breakpoint(120, thresholds) == "today"
    assert resolve_breakpoint(310, thresholds) == "today_tomorrow"
    assert resolve_breakpoint(900, thresholds) == "week"
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `python -m pytest tests/test_responsive.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: 최소 구현 작성**

`src/teacher_widgets/core/responsive.py`:
```python
"""위젯 크기 기반 반응형 계산."""

from __future__ import annotations


def scale_factor(
    current: tuple[int, int],
    base: tuple[int, int],
    min_factor: float = 0.6,
    max_factor: float = 3.0,
) -> float:
    """현재 크기/기준 크기 비율 중 더 작은 축을 채택하고 범위로 클램프."""
    cw, ch = current
    bw, bh = base
    ratio = min(cw / bw, ch / bh)
    return max(min_factor, min(max_factor, ratio))


def scaled_font_pt(
    base_pt: float,
    factor: float,
    min_pt: int = 8,
    max_pt: int = 72,
) -> int:
    """기준 폰트 pt에 배율을 적용하고 정수로 반올림 후 클램프."""
    value = round(base_pt * factor)
    return max(min_pt, min(max_pt, value))


def resolve_breakpoint(width: int, thresholds: list[tuple[int, str]]) -> str:
    """width 이하의 가장 큰 임계값에 해당하는 라벨 반환."""
    chosen = thresholds[0][1]
    for threshold, label in sorted(thresholds):
        if width >= threshold:
            chosen = label
    return chosen
```

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `python -m pytest tests/test_responsive.py -v`
Expected: 6 passed

- [ ] **Step 5: 커밋**

```bash
git add src/teacher_widgets/core/responsive.py tests/test_responsive.py
git commit -m "feat: 반응형 스케일·폰트·내용구간 계산 구현

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: 공통 베이스 위젯 (base_widget)

**Files:**
- Create: `src/teacher_widgets/core/base_widget.py`
- Test: `tests/test_base_widget.py`

**Interfaces:**
- Consumes: `ConfigStore` (Task 2)
- Produces:
  - `class BaseWidget(QtWidgets.QWidget)`
    - `__init__(self, widget_name: str, store: ConfigStore)`
    - `widget_name: str`
    - `restore_geometry() -> None`  (config의 geometry를 창에 적용)
    - `persist_geometry() -> None`  (현재 창 geometry를 config에 저장+save)
    - `apply_opacity(percent: int) -> None`
    - `set_locked(locked: bool) -> None`  (이동/리사이즈 잠금)
    - `hide_to_config() -> None`  (창 숨김 + config visible=False + save)
    - `content_layout: QtWidgets.QVBoxLayout`  (서브클래스가 위젯을 담는 영역)
    - `BASE_SIZE: tuple[int, int]`  (서브클래스가 오버라이드, 기본 (220, 140))

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_base_widget.py`:
```python
from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.core.base_widget import BaseWidget


def make_store(tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    return store


def test_restore_geometry_applies_saved_position(qtbot, tmp_path):
    store = make_store(tmp_path)
    store.set_widget_geometry("clock", [50, 60, 300, 160])
    w = BaseWidget("clock", store)
    qtbot.addWidget(w)
    w.restore_geometry()
    g = w.geometry()
    assert (g.x(), g.y(), g.width(), g.height()) == (50, 60, 300, 160)


def test_persist_geometry_writes_current_position(qtbot, tmp_path):
    store = make_store(tmp_path)
    w = BaseWidget("clock", store)
    qtbot.addWidget(w)
    w.setGeometry(11, 22, 240, 150)
    w.persist_geometry()
    assert store.get_widget("clock")["geometry"] == [11, 22, 240, 150]
    assert (tmp_path / "config.json").exists()


def test_hide_to_config_marks_invisible(qtbot, tmp_path):
    store = make_store(tmp_path)
    w = BaseWidget("clock", store)
    qtbot.addWidget(w)
    w.show()
    w.hide_to_config()
    assert w.isVisible() is False
    assert store.get_widget("clock")["visible"] is False


def test_apply_opacity_sets_window_opacity(qtbot, tmp_path):
    store = make_store(tmp_path)
    w = BaseWidget("clock", store)
    qtbot.addWidget(w)
    w.apply_opacity(50)
    assert abs(w.windowOpacity() - 0.5) < 0.01
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `python -m pytest tests/test_base_widget.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: 최소 구현 작성**

`src/teacher_widgets/core/base_widget.py`:
```python
"""모든 위젯이 상속하는 공통 베이스: 프레임리스·반투명·이동·리사이즈·저장."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from .config_store import ConfigStore


class BaseWidget(QtWidgets.QWidget):
    BASE_SIZE: tuple[int, int] = (220, 140)

    def __init__(self, widget_name: str, store: ConfigStore):
        super().__init__()
        self.widget_name = widget_name
        self.store = store
        self._locked = False
        self._drag_offset: QtCore.QPoint | None = None

        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.Tool
            | QtCore.Qt.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        self.content_layout = QtWidgets.QVBoxLayout(self)
        self.content_layout.setContentsMargins(12, 12, 12, 12)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)

        self.apply_opacity(self.store.get_opacity())
        self.set_locked(self.store.data.get("layout_locked", False))

    # --- 위치/크기 저장·복원 ---
    def restore_geometry(self) -> None:
        x, y, w, h = self.store.get_widget(self.widget_name)["geometry"]
        self.setGeometry(int(x), int(y), int(w), int(h))

    def persist_geometry(self) -> None:
        g = self.geometry()
        self.store.set_widget_geometry(
            self.widget_name, [g.x(), g.y(), g.width(), g.height()]
        )
        self.store.save()

    # --- 표시/숨김 ---
    def hide_to_config(self) -> None:
        self.hide()
        self.store.set_widget_visible(self.widget_name, False)
        self.store.save()

    # --- 외형 ---
    def apply_opacity(self, percent: int) -> None:
        self.setWindowOpacity(max(0.2, min(1.0, percent / 100)))

    def set_locked(self, locked: bool) -> None:
        self._locked = bool(locked)

    # --- 드래그 이동 ---
    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton and not self._locked:
            self._drag_offset = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._drag_offset is not None and not self._locked:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._drag_offset is not None:
            self._drag_offset = None
            self.persist_geometry()
            event.accept()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self.on_resized(self.width(), self.height())

    def on_resized(self, width: int, height: int) -> None:
        """서브클래스가 반응형 갱신을 위해 오버라이드."""

    # --- 우클릭 메뉴 ---
    def _show_menu(self, pos: QtCore.QPoint) -> None:
        menu = QtWidgets.QMenu(self)
        lock_action = menu.addAction("이동 잠금 해제" if self._locked else "이동 잠금")
        close_action = menu.addAction("이 위젯 닫기")
        chosen = menu.exec(self.mapToGlobal(pos))
        if chosen == lock_action:
            self.set_locked(not self._locked)
        elif chosen == close_action:
            self.hide_to_config()
```

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `python -m pytest tests/test_base_widget.py -v`
Expected: 4 passed

- [ ] **Step 5: 커밋**

```bash
git add src/teacher_widgets/core/base_widget.py tests/test_base_widget.py
git commit -m "feat: 프레임리스 공통 베이스 위젯(이동·리사이즈·저장·숨김) 구현

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: 시계 위젯 (clock)

**Files:**
- Create: `src/teacher_widgets/widgets/clock.py`
- Test: `tests/test_clock.py`

**Interfaces:**
- Consumes: `BaseWidget` (Task 4), `ConfigStore` (Task 2), `responsive.scale_factor/scaled_font_pt` (Task 3)
- Produces:
  - `format_clock(dt: datetime.datetime, hour24: bool = True, show_seconds: bool = True) -> dict`
    → `{"time": str, "date": str, "weekday": str}` (weekday는 한글: 월/화/수/목/금/토/일)
  - `class ClockWidget(BaseWidget)` (widget_name="clock")

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_clock.py`:
```python
import datetime

from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.widgets.clock import format_clock, ClockWidget


def test_format_clock_24h_with_seconds():
    dt = datetime.datetime(2026, 6, 29, 14, 5, 9)  # 월요일
    out = format_clock(dt, hour24=True, show_seconds=True)
    assert out["time"] == "14:05:09"
    assert out["date"] == "2026-06-29"
    assert out["weekday"] == "월"


def test_format_clock_12h_without_seconds():
    dt = datetime.datetime(2026, 6, 29, 14, 5, 9)
    out = format_clock(dt, hour24=False, show_seconds=False)
    assert out["time"] == "오후 2:05"


def test_clock_widget_uses_clock_name(qtbot, tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    w = ClockWidget(store)
    qtbot.addWidget(w)
    assert w.widget_name == "clock"
    # 라벨이 비어있지 않게 즉시 한 번 갱신되어야 함
    assert w.time_label.text() != ""
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `python -m pytest tests/test_clock.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: 최소 구현 작성**

`src/teacher_widgets/widgets/clock.py`:
```python
"""시계 위젯: 시각 + 날짜 + 한글 요일."""

from __future__ import annotations

import datetime

from PySide6 import QtCore, QtWidgets

from ..core.base_widget import BaseWidget
from ..core.config_store import ConfigStore
from ..core.responsive import scale_factor, scaled_font_pt

_WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]


def format_clock(
    dt: datetime.datetime, hour24: bool = True, show_seconds: bool = True
) -> dict:
    if hour24:
        fmt = "%H:%M:%S" if show_seconds else "%H:%M"
        time_str = dt.strftime(fmt)
    else:
        ampm = "오전" if dt.hour < 12 else "오후"
        hour12 = dt.hour % 12 or 12
        if show_seconds:
            time_str = f"{ampm} {hour12}:{dt.minute:02d}:{dt.second:02d}"
        else:
            time_str = f"{ampm} {hour12}:{dt.minute:02d}"
    return {
        "time": time_str,
        "date": dt.strftime("%Y-%m-%d"),
        "weekday": _WEEKDAYS[dt.weekday()],
    }


class ClockWidget(BaseWidget):
    BASE_SIZE = (220, 128)

    def __init__(self, store: ConfigStore):
        super().__init__("clock", store)
        self.hour24 = True
        self.show_seconds = True

        self.time_label = QtWidgets.QLabel("", alignment=QtCore.Qt.AlignCenter)
        self.date_label = QtWidgets.QLabel("", alignment=QtCore.Qt.AlignCenter)
        self.time_label.setStyleSheet("color: #2b2b2b; font-weight: 600;")
        self.date_label.setStyleSheet("color: #666;")
        self.content_layout.addWidget(self.time_label)
        self.content_layout.addWidget(self.date_label)

        self._tick = QtCore.QTimer(self)
        self._tick.timeout.connect(self._refresh)
        self._tick.start(1000)
        self._refresh()

    def paintEvent(self, event):  # 반투명 라운드 배경
        from PySide6 import QtGui

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(QtGui.QColor(255, 255, 255, 235))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 16, 16)

    def _refresh(self) -> None:
        parts = format_clock(datetime.datetime.now(), self.hour24, self.show_seconds)
        self.time_label.setText(parts["time"])
        self.date_label.setText(f"{parts['date']} ({parts['weekday']})")
        self._apply_responsive()

    def _apply_responsive(self) -> None:
        factor = scale_factor((self.width(), self.height()), self.BASE_SIZE)
        self.time_label.setStyleSheet(
            f"color:#2b2b2b; font-weight:600; font-size:{scaled_font_pt(28, factor)}pt;"
        )
        self.date_label.setStyleSheet(
            f"color:#666; font-size:{scaled_font_pt(11, factor)}pt;"
        )

    def on_resized(self, width: int, height: int) -> None:
        self._apply_responsive()
```

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `python -m pytest tests/test_clock.py -v`
Expected: 3 passed

- [ ] **Step 5: 커밋**

```bash
git add src/teacher_widgets/widgets/clock.py tests/test_clock.py
git commit -m "feat: 시계 위젯(시각·날짜·한글요일·반응형) 구현

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: 타이머 위젯 (timer)

**Files:**
- Create: `src/teacher_widgets/widgets/timer.py`
- Test: `tests/test_timer.py`

**Interfaces:**
- Consumes: `BaseWidget` (Task 4), `ConfigStore` (Task 2)
- Produces:
  - `format_mmss(total_seconds: int) -> str`  → `"MM:SS"`
  - `class TimerModel`
    - `__init__(self, minutes: int = 5, seconds: int = 0)`
    - `state: str`  ∈ {"idle", "running", "paused", "finished"}
    - `remaining: int`  (초)
    - `set_duration(minutes: int, seconds: int) -> None`
    - `start() -> None`
    - `pause() -> None`
    - `reset() -> None`
    - `tick() -> int`  (1초 감소, 0 도달 시 state="finished", remaining 반환)
  - `class TimerWidget(BaseWidget)` (widget_name="timer")

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_timer.py`:
```python
from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.widgets.timer import TimerModel, format_mmss, TimerWidget


def test_format_mmss():
    assert format_mmss(0) == "00:00"
    assert format_mmss(65) == "01:05"
    assert format_mmss(600) == "10:00"


def test_model_starts_idle_with_duration():
    m = TimerModel(5, 0)
    assert m.state == "idle"
    assert m.remaining == 300


def test_model_tick_decrements_only_when_running():
    m = TimerModel(0, 3)
    m.tick()
    assert m.remaining == 3  # idle 상태에서는 감소 안 함
    m.start()
    assert m.tick() == 2
    assert m.tick() == 1


def test_model_reaches_finished_at_zero():
    m = TimerModel(0, 1)
    m.start()
    m.tick()
    assert m.remaining == 0
    assert m.state == "finished"


def test_model_pause_and_reset():
    m = TimerModel(1, 0)
    m.start()
    m.tick()
    m.pause()
    assert m.state == "paused"
    paused_remaining = m.remaining
    m.tick()
    assert m.remaining == paused_remaining  # paused면 감소 안 함
    m.reset()
    assert m.state == "idle"
    assert m.remaining == 60


def test_timer_widget_name(qtbot, tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    w = TimerWidget(store)
    qtbot.addWidget(w)
    assert w.widget_name == "timer"
    assert w.display_label.text() == "05:00"
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `python -m pytest tests/test_timer.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: 최소 구현 작성**

`src/teacher_widgets/widgets/timer.py`:
```python
"""타이머 위젯: 순수 모델 + GUI."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from ..core.base_widget import BaseWidget
from ..core.config_store import ConfigStore


def format_mmss(total_seconds: int) -> str:
    total_seconds = max(0, int(total_seconds))
    return f"{total_seconds // 60:02d}:{total_seconds % 60:02d}"


class TimerModel:
    def __init__(self, minutes: int = 5, seconds: int = 0):
        self._initial = minutes * 60 + seconds
        self.remaining = self._initial
        self.state = "idle"

    def set_duration(self, minutes: int, seconds: int) -> None:
        self._initial = minutes * 60 + seconds
        self.remaining = self._initial
        self.state = "idle"

    def start(self) -> None:
        if self.remaining > 0:
            self.state = "running"

    def pause(self) -> None:
        if self.state == "running":
            self.state = "paused"

    def reset(self) -> None:
        self.remaining = self._initial
        self.state = "idle"

    def tick(self) -> int:
        if self.state == "running":
            self.remaining = max(0, self.remaining - 1)
            if self.remaining == 0:
                self.state = "finished"
        return self.remaining


class TimerWidget(BaseWidget):
    BASE_SIZE = (220, 180)

    def __init__(self, store: ConfigStore):
        super().__init__("timer", store)
        saved = store.data.get("timer", {"minutes": 5, "seconds": 0})
        self.model = TimerModel(saved.get("minutes", 5), saved.get("seconds", 0))

        self.display_label = QtWidgets.QLabel(
            format_mmss(self.model.remaining), alignment=QtCore.Qt.AlignCenter
        )
        self.display_label.setStyleSheet("font-size:40pt; font-weight:700; color:#2b2b2b;")
        self.content_layout.addWidget(self.display_label)

        buttons = QtWidgets.QHBoxLayout()
        self.start_btn = QtWidgets.QPushButton("시작")
        self.reset_btn = QtWidgets.QPushButton("리셋")
        self.start_btn.clicked.connect(self._toggle)
        self.reset_btn.clicked.connect(self._reset)
        buttons.addWidget(self.start_btn)
        buttons.addWidget(self.reset_btn)
        self.content_layout.addLayout(buttons)

        self._tick = QtCore.QTimer(self)
        self._tick.timeout.connect(self._on_tick)
        self._tick.start(1000)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(QtGui.QColor(255, 255, 255, 235))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 16, 16)

    def _toggle(self) -> None:
        if self.model.state == "running":
            self.model.pause()
            self.start_btn.setText("시작")
        else:
            self.model.start()
            self.start_btn.setText("일시정지")

    def _reset(self) -> None:
        self.model.reset()
        self.start_btn.setText("시작")
        self.display_label.setText(format_mmss(self.model.remaining))

    def _on_tick(self) -> None:
        before = self.model.state
        self.model.tick()
        self.display_label.setText(format_mmss(self.model.remaining))
        if before == "running" and self.model.state == "finished":
            QtWidgets.QApplication.beep()
            self.start_btn.setText("시작")
```

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `python -m pytest tests/test_timer.py -v`
Expected: 6 passed

- [ ] **Step 5: 커밋**

```bash
git add src/teacher_widgets/widgets/timer.py tests/test_timer.py
git commit -m "feat: 타이머 위젯(순수 모델 + GUI) 구현

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: 메모 위젯 (memo)

**Files:**
- Create: `src/teacher_widgets/widgets/memo.py`
- Test: `tests/test_memo.py`

**Interfaces:**
- Consumes: `BaseWidget` (Task 4), `ConfigStore` (Task 2)
- Produces:
  - `get_memo_text(store: ConfigStore, name: str) -> str`
  - `set_memo_text(store: ConfigStore, name: str, text: str) -> None`  (config의 `memo_texts[name]`에 저장+save)
  - `class MemoWidget(BaseWidget)`  (`__init__(self, store, name="memo")` — 여러 인스턴스 지원)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_memo.py`:
```python
from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.widgets.memo import (
    get_memo_text,
    set_memo_text,
    MemoWidget,
)


def test_memo_text_roundtrip(tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    set_memo_text(store, "memo_2", "준비물: 가위, 풀")
    assert get_memo_text(store, "memo_2") == "준비물: 가위, 풀"


def test_get_memo_text_default_empty(tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    assert get_memo_text(store, "memo_9") == ""


def test_memo_widget_loads_saved_text(qtbot, tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    set_memo_text(store, "memo_1", "오늘 회의 3시")
    w = MemoWidget(store, "memo_1")
    qtbot.addWidget(w)
    assert w.widget_name == "memo_1"
    assert w.editor.toPlainText() == "오늘 회의 3시"


def test_memo_widget_saves_on_text_change(qtbot, tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    w = MemoWidget(store, "memo_1")
    qtbot.addWidget(w)
    w.editor.setPlainText("새 메모")
    w._save_text()
    assert get_memo_text(store, "memo_1") == "새 메모"
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `python -m pytest tests/test_memo.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: 최소 구현 작성**

`src/teacher_widgets/widgets/memo.py`:
```python
"""메모 위젯: 여러 인스턴스 지원, 자동 저장."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from ..core.base_widget import BaseWidget
from ..core.config_store import ConfigStore


def get_memo_text(store: ConfigStore, name: str) -> str:
    return store.data.setdefault("memo_texts", {}).get(name, "")


def set_memo_text(store: ConfigStore, name: str, text: str) -> None:
    store.data.setdefault("memo_texts", {})[name] = text
    store.save()


class MemoWidget(BaseWidget):
    BASE_SIZE = (240, 190)

    def __init__(self, store: ConfigStore, name: str = "memo"):
        super().__init__(name, store)
        self.editor = QtWidgets.QPlainTextEdit()
        self.editor.setPlainText(get_memo_text(store, name))
        self.editor.setStyleSheet(
            "background: transparent; border: none; font-size: 12pt; color:#2b2b2b;"
        )
        self.content_layout.addWidget(self.editor)

        self._save_timer = QtCore.QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(800)
        self._save_timer.timeout.connect(self._save_text)
        self.editor.textChanged.connect(self._save_timer.start)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(QtGui.QColor(255, 249, 196, 240))  # 포스트잇 노랑
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 12, 12)

    def _save_text(self) -> None:
        set_memo_text(self.store, self.widget_name, self.editor.toPlainText())
```

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `python -m pytest tests/test_memo.py -v`
Expected: 4 passed

- [ ] **Step 5: 커밋**

```bash
git add src/teacher_widgets/widgets/memo.py tests/test_memo.py
git commit -m "feat: 메모 위젯(다중 인스턴스·자동저장) 구현

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8: 위젯 등록 컨트롤러 (registry)

**Files:**
- Create: `src/teacher_widgets/core/registry.py`
- Test: `tests/test_registry.py`

**Interfaces:**
- Consumes: `ConfigStore` (Task 2), `BaseWidget` (Task 4)
- Produces:
  - `class WidgetRegistry`
    - `__init__(self, store: ConfigStore)`
    - `register(self, name: str, factory: Callable[[], BaseWidget]) -> None`
    - `names() -> list[str]`
    - `is_visible(name: str) -> bool`  (config 기준)
    - `show(name: str) -> BaseWidget`  (없으면 factory로 생성, geometry 복원, 표시, config visible=True+save)
    - `hide(name: str) -> None`  (인스턴스 있으면 hide_to_config)
    - `restore_visible() -> None`  (config에서 visible=True인 등록 위젯을 모두 show)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_registry.py`:
```python
from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.core.base_widget import BaseWidget
from teacher_widgets.core.registry import WidgetRegistry


def make(tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    return store


def test_register_and_names(qtbot, tmp_path):
    store = make(tmp_path)
    reg = WidgetRegistry(store)
    reg.register("clock", lambda: BaseWidget("clock", store))
    reg.register("timer", lambda: BaseWidget("timer", store))
    assert reg.names() == ["clock", "timer"]


def test_show_creates_and_marks_visible(qtbot, tmp_path):
    store = make(tmp_path)
    reg = WidgetRegistry(store)
    reg.register("clock", lambda: BaseWidget("clock", store))
    w = reg.show("clock")
    qtbot.addWidget(w)
    assert w.isVisible() is True
    assert store.get_widget("clock")["visible"] is True
    # 두 번째 show는 같은 인스턴스 반환
    assert reg.show("clock") is w


def test_hide_marks_invisible(qtbot, tmp_path):
    store = make(tmp_path)
    reg = WidgetRegistry(store)
    reg.register("clock", lambda: BaseWidget("clock", store))
    w = reg.show("clock")
    qtbot.addWidget(w)
    reg.hide("clock")
    assert store.get_widget("clock")["visible"] is False


def test_restore_visible_only_shows_visible(qtbot, tmp_path):
    store = make(tmp_path)
    store.set_widget_visible("clock", True)
    store.set_widget_visible("timer", False)
    reg = WidgetRegistry(store)
    reg.register("clock", lambda: BaseWidget("clock", store))
    reg.register("timer", lambda: BaseWidget("timer", store))
    reg.restore_visible()
    assert reg.is_visible("clock") is True
    assert reg.is_visible("timer") is False
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `python -m pytest tests/test_registry.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: 최소 구현 작성**

`src/teacher_widgets/core/registry.py`:
```python
"""위젯 등록·표시·숨김 컨트롤러 (트레이 UI와 분리하여 테스트 가능)."""

from __future__ import annotations

from typing import Callable

from .base_widget import BaseWidget
from .config_store import ConfigStore


class WidgetRegistry:
    def __init__(self, store: ConfigStore):
        self.store = store
        self._factories: dict[str, Callable[[], BaseWidget]] = {}
        self._instances: dict[str, BaseWidget] = {}

    def register(self, name: str, factory: Callable[[], BaseWidget]) -> None:
        self._factories[name] = factory

    def names(self) -> list[str]:
        return list(self._factories.keys())

    def is_visible(self, name: str) -> bool:
        return self.store.get_widget(name)["visible"]

    def show(self, name: str) -> BaseWidget:
        widget = self._instances.get(name)
        if widget is None:
            widget = self._factories[name]()
            self._instances[name] = widget
        widget.restore_geometry()
        widget.show()
        self.store.set_widget_visible(name, True)
        self.store.save()
        return widget

    def hide(self, name: str) -> None:
        widget = self._instances.get(name)
        if widget is not None:
            widget.hide_to_config()
        else:
            self.store.set_widget_visible(name, False)
            self.store.save()

    def restore_visible(self) -> None:
        for name in self._factories:
            if self.is_visible(name):
                self.show(name)
```

- [ ] **Step 4: 테스트 실행하여 통과 확인**

Run: `python -m pytest tests/test_registry.py -v`
Expected: 4 passed

- [ ] **Step 5: 커밋**

```bash
git add src/teacher_widgets/core/registry.py tests/test_registry.py
git commit -m "feat: 위젯 등록·표시·숨김 컨트롤러 구현

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 9: 트레이 런처 + 진입점 (tray, main)

**Files:**
- Create: `src/teacher_widgets/tray.py`
- Create: `src/teacher_widgets/main.py`
- Create: `assets/icon.png`
- Test: `tests/test_tray.py`

**Interfaces:**
- Consumes: `WidgetRegistry` (Task 8), `ConfigStore` (Task 2), 위젯 클래스 (Task 5~7)
- Produces:
  - `build_tray_menu(registry: WidgetRegistry) -> QtWidgets.QMenu`  (각 위젯 토글 체크 액션 + 종료)
  - `class TrayLauncher` (`__init__(self, app, registry)`)
  - `main() -> int`  (config 경로 결정 → 위젯 등록 → 복원 → 트레이 → app.exec)

- [ ] **Step 1: 임시 아이콘 생성**

```bash
python - <<'PY'
from PySide6 import QtGui, QtCore
QtGui.QGuiApplication  # noqa
img = QtGui.QImage(64, 64, QtGui.QImage.Format_ARGB32)
img.fill(QtGui.QColor("#7cc6a6"))
img.save("assets/icon.png")
print("icon written")
PY
```

Expected: `assets/icon.png` 생성. (실패 시 임의 64x64 png를 직접 배치)

- [ ] **Step 2: 실패하는 테스트 작성**

`tests/test_tray.py`:
```python
from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.core.base_widget import BaseWidget
from teacher_widgets.core.registry import WidgetRegistry
from teacher_widgets.tray import build_tray_menu


def test_build_tray_menu_has_action_per_widget_plus_quit(qtbot, tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    reg = WidgetRegistry(store)
    reg.register("clock", lambda: BaseWidget("clock", store))
    reg.register("memo", lambda: BaseWidget("memo", store))

    menu = build_tray_menu(reg)
    texts = [a.text() for a in menu.actions() if a.text()]
    assert "clock" in texts
    assert "memo" in texts
    assert "종료" in texts


def test_tray_menu_toggle_action_is_checkable(qtbot, tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    store.set_widget_visible("clock", True)
    reg = WidgetRegistry(store)
    reg.register("clock", lambda: BaseWidget("clock", store))
    menu = build_tray_menu(reg)
    clock_action = next(a for a in menu.actions() if a.text() == "clock")
    assert clock_action.isCheckable() is True
    assert clock_action.isChecked() is True
```

- [ ] **Step 3: 테스트 실행하여 실패 확인**

Run: `python -m pytest tests/test_tray.py -v`
Expected: FAIL (ModuleNotFoundError: teacher_widgets.tray)

- [ ] **Step 4: tray.py 구현**

`src/teacher_widgets/tray.py`:
```python
"""시스템 트레이 런처."""

from __future__ import annotations

from pathlib import Path

from PySide6 import QtGui, QtWidgets

from .core.registry import WidgetRegistry

_ICON_PATH = Path(__file__).resolve().parents[2] / "assets" / "icon.png"


def build_tray_menu(registry: WidgetRegistry) -> QtWidgets.QMenu:
    menu = QtWidgets.QMenu()
    for name in registry.names():
        action = menu.addAction(name)
        action.setCheckable(True)
        action.setChecked(registry.is_visible(name))

        def make_handler(widget_name: str):
            def handler(checked: bool):
                if checked:
                    registry.show(widget_name)
                else:
                    registry.hide(widget_name)

            return handler

        action.toggled.connect(make_handler(name))
    menu.addSeparator()
    menu.addAction("종료")
    return menu


class TrayLauncher:
    def __init__(self, app: QtWidgets.QApplication, registry: WidgetRegistry):
        self.app = app
        self.registry = registry
        icon = QtGui.QIcon(str(_ICON_PATH))
        self.tray = QtWidgets.QSystemTrayIcon(icon)
        self.tray.setToolTip("교사용 위젯")
        self.menu = build_tray_menu(registry)
        quit_action = next(a for a in self.menu.actions() if a.text() == "종료")
        quit_action.triggered.connect(self.app.quit)
        self.tray.setContextMenu(self.menu)
        self.tray.show()
```

- [ ] **Step 5: main.py 구현**

`src/teacher_widgets/main.py`:
```python
"""진입점: 설정 로드 → 위젯 등록 → 복원 → 트레이 → 실행."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6 import QtWidgets

from .core.config_store import ConfigStore
from .core.registry import WidgetRegistry
from .tray import TrayLauncher
from .widgets.clock import ClockWidget
from .widgets.timer import TimerWidget
from .widgets.memo import MemoWidget


def _config_path() -> Path:
    if getattr(sys, "frozen", False):  # PyInstaller exe
        base = Path(sys.executable).parent
    else:
        base = Path.cwd()
    return base / "teacher-widgets-data" / "config.json"


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # 위젯 닫아도 트레이 유지

    store = ConfigStore(_config_path())
    store.load()

    registry = WidgetRegistry(store)
    registry.register("clock", lambda: ClockWidget(store))
    registry.register("timer", lambda: TimerWidget(store))
    registry.register("memo", lambda: MemoWidget(store, "memo"))

    # 최초 실행: config에 위젯 기록이 없으면 시계만 기본 표시
    if not store.data["widgets"]:
        store.set_widget_visible("clock", True)

    registry.restore_visible()
    TrayLauncher(app, registry)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: 테스트 실행하여 통과 확인**

Run: `python -m pytest tests/test_tray.py -v`
Expected: 2 passed

- [ ] **Step 7: 전체 테스트 + 수동 실행 확인**

Run: `python -m pytest -v`
Expected: 모든 테스트 통과.

Run (수동, GUI 확인): `python -m teacher_widgets.main` *(src 레이아웃이므로 `cd src && python -m teacher_widgets.main` 또는 `PYTHONPATH=src python -m teacher_widgets.main`)*
Expected: 트레이 아이콘 표시, 시계 위젯이 화면에 뜸. 트레이 메뉴에서 timer/memo 토글 가능, 드래그 이동 후 재실행 시 위치 유지.

- [ ] **Step 8: 커밋**

```bash
git add src/teacher_widgets/tray.py src/teacher_widgets/main.py tests/test_tray.py assets/icon.png
git commit -m "feat: 시스템 트레이 런처와 진입점 구현

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 10: PyInstaller 배포 + 시작프로그램 스크립트

**Files:**
- Create: `build/teacher_widgets.spec`
- Create: `build/install_startup.bat`
- Create: `build/uninstall_startup.bat`

**Interfaces:**
- Consumes: `main.py` (Task 9)
- Produces: 배포용 `dist/TeacherWidgets/TeacherWidgets.exe`

- [ ] **Step 1: 진입 스크립트 생성**

`build/run.py` (PyInstaller 진입점, src 레이아웃 흡수):
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from teacher_widgets.main import main

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: PyInstaller 스펙 작성**

`build/teacher_widgets.spec`:
```python
# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

ROOT = Path(SPECPATH).parent

a = Analysis(
    [str(ROOT / "build" / "run.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=[(str(ROOT / "assets" / "icon.png"), "assets")],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name="TeacherWidgets", console=False,
)
coll = COLLECT(
    exe, a.binaries, a.datas,
    name="TeacherWidgets",
)
```

- [ ] **Step 3: 빌드 실행**

Run: `pyinstaller build/teacher_widgets.spec --noconfirm`
Expected: `dist/TeacherWidgets/TeacherWidgets.exe` 생성.

- [ ] **Step 4: 빌드 산출물 수동 실행 확인**

Run: `dist/TeacherWidgets/TeacherWidgets.exe` 더블클릭(또는 셸에서 실행)
Expected: 파이썬 미설치 가정 환경에서도 트레이 아이콘 + 시계 위젯 표시. `dist/TeacherWidgets/teacher-widgets-data/config.json` 생성됨.

- [ ] **Step 5: 시작프로그램 스크립트 작성 (레퍼런스 계승)**

`build/install_startup.bat`:
```bat
@echo off
setlocal
cd /d "%~dp0"

set "EXE="
if exist "%cd%\dist\TeacherWidgets\TeacherWidgets.exe" (
  set "EXE=%cd%\dist\TeacherWidgets\TeacherWidgets.exe"
  set "WORKDIR=%cd%\dist\TeacherWidgets"
)
if not defined EXE if exist "%cd%\TeacherWidgets\TeacherWidgets.exe" (
  set "EXE=%cd%\TeacherWidgets\TeacherWidgets.exe"
  set "WORKDIR=%cd%\TeacherWidgets"
)
if not defined EXE (
  echo Built exe was not found. Run pyinstaller first.
  pause
  exit /b 1
)
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT=%STARTUP%\TeacherWidgets.lnk"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%SHORTCUT%');" ^
  "$s.TargetPath='%EXE%';$s.WorkingDirectory='%WORKDIR%';" ^
  "$s.IconLocation='%EXE%,0';$s.WindowStyle=7;$s.Save()"
echo Startup shortcut created: %SHORTCUT%
pause
```

`build/uninstall_startup.bat`:
```bat
@echo off
setlocal
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT=%STARTUP%\TeacherWidgets.lnk"
if exist "%SHORTCUT%" (
  del "%SHORTCUT%"
  echo Startup shortcut removed.
) else (
  echo Startup shortcut was not found.
)
pause
```

- [ ] **Step 6: .gitignore 갱신 확인**

`build/`, `dist/`는 산출물이므로 커밋하지 않는다. 기존 `.gitignore`에 `build/`, `dist/`가 있는지 확인하고, 스크립트/스펙은 명시적으로 추적:
```bash
git add -f build/run.py build/teacher_widgets.spec build/install_startup.bat build/uninstall_startup.bat
```

(주의: 루트 `.gitignore`의 `build/` 규칙이 스펙 파일까지 무시하므로 `-f`로 강제 추가하거나, `.gitignore`에서 `build/`를 `build/*.tmp` 등으로 좁힌다.)

- [ ] **Step 7: 커밋**

```bash
git add -f build/run.py build/teacher_widgets.spec build/install_startup.bat build/uninstall_startup.bat
git commit -m "build: PyInstaller 배포 스펙과 시작프로그램 스크립트 추가

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 자기 점검 (Self-Review)

**1. Spec 커버리지 (Phase 0 + Phase 1 범위)**
- 공통 엔진 base_widget(프레임리스·반투명·이동·리사이즈·위치저장·숨기기) → Task 4 ✅
- 반응형(폰트/내용 구간) → Task 3 + 시계 적용(Task 5) ✅
- config 단일 저장소 → Task 2 ✅
- 트레이 런처(on/off·종료) → Task 8(컨트롤러) + Task 9(UI) ✅
- 멀티모니터 위치 저장·복원 → geometry 가상좌표 저장(Task 4, 검증은 Task 9 수동) ✅
- 시계(날짜·요일) → Task 5 ✅ / 타이머 → Task 6 ✅ / 메모(다중) → Task 7 ✅
- PyInstaller 단일 exe 배포 + 시작프로그램 → Task 10 ✅
- 검증 기준(이동·리사이즈 반응형, 멀티모니터 복원, 숨김/재표시, exe 실행) → Task 9 Step 7 + Task 10 Step 4 ✅

**2. 플레이스홀더 스캔:** "TBD/적절히 처리" 등 없음. 모든 코드 스텝에 실제 코드 포함 ✅

**3. 타입 일관성:** `ConfigStore.get_widget()→dict`, `set_widget_geometry(name, list)`, `BaseWidget(name, store)`, `WidgetRegistry.show()→BaseWidget` 등 Task 간 시그니처 일치 확인 ✅

**미해결 메모(후속 Phase, 본 계획 범위 외):** 출결 Excel 양식, 주간학습계획 API 스키마, 자동 업데이트 — 설계 문서 §12에 기록됨.
