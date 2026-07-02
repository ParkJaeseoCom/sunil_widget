# Phase 4-A RemoteWidget 공통화 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 시간표·주간계획·급식·날씨 4개 위젯에 4중 복제된 원격 수명주기(~100줄/위젯)를 `RemoteWidget(BaseWidget)` 중간 베이스로 추출하고, 429 지수 백오프와 시작 지터를 중앙 refresh에 넣는다. (Phase 3 최종 리뷰 지시 사항 — Phase 4 신규 위젯의 전제)

**Architecture:** `core/remote_widget.py`에 상태(_worker/_data/cache_path/_tier)·수명주기(showEvent/hideEvent/_shutdown_worker)·refresh(백오프·지터·재진입 가드)·_on_fetch_ok/_on_fetch_failed·paintEvent·tier 스켈레톤을 둔다. 서브클래스는 `CONFIG_KEY`·`TIERS`(없으면 None)·`_make_worker()`·`_render()`만 제공한다. **기존 136 테스트가 리팩터링의 동작 보증** — 테스트 파일은 원칙적으로 수정하지 않는다(리팩터링 검증 원칙). 신규 동작(백오프·지터)만 새 테스트를 추가한다.

**Tech Stack:** 기존과 동일 (PySide6, pytest). 새 의존성 없음.

## Global Constraints

- 동작 보존 리팩터링: 기존 136 테스트를 **수정 없이** 통과시킬 것(테스트가 참조하는 공개 표면 유지 — `render_grid/render_plan/render_meal/render_weather`, `days_text/menu_text/body_text`, `apply_data`(timetable), `_on_fetch_failed`, `status_label`, `header_label`, `_cells`, `current_tier`, `cache_path`, `_buttons` 등).
- `_skip_initial_fetch` 가드 의미 유지 (showEvent에서 설정 키로 확인).
- 새 동작: ① 실패 메시지에 "429" 포함 시 `_backoff_until = now + 2h` 설정, 자동 refresh는 그때까지 스킵, **수동 refresh(메뉴)는 `force=True`로 우회**. ② showEvent의 초기 fetch는 0~15초 랜덤 지터 후 실행(`QTimer.singleShot`), 테스트·수동은 지터 없음.
- 실행: `.venv/Scripts/python.exe -m pytest -v` (경로 공백·한글 → 따옴표), offscreen.
- 커밋 footer: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

## 파일 구조

```
src/teacher_widgets/core/remote_widget.py   # (신규) RemoteWidget
src/teacher_widgets/widgets/timetable.py    # (수정) RemoteWidget 상속 마이그레이션
src/teacher_widgets/widgets/weekly_plan.py  # (수정) 〃
src/teacher_widgets/widgets/meal.py         # (수정) 〃
src/teacher_widgets/widgets/weather.py      # (수정) 〃
tests/test_remote_widget.py                 # (신규) 백오프·지터·수명주기
```

---

## Task 1: RemoteWidget 베이스 (core/remote_widget.py)

**Files:**
- Create: `src/teacher_widgets/core/remote_widget.py`
- Test: `tests/test_remote_widget.py`

**Interfaces:**
- Consumes: `BaseWidget`, `data_remote.read_cache/write_cache`, `responsive.resolve_breakpoint`.
- Produces: `class RemoteWidget(BaseWidget)`
  - 클래스 속성(서브클래스 지정): `CONFIG_KEY: str = ""`, `TIERS: list | None = None`, `BASE_SIZE` (BaseWidget 상속)
  - `__init__(self, store)`: `super().__init__(self.CONFIG_KEY, store)`; `self.cache_path = Path(store.path).parent / "cache" / f"{self.CONFIG_KEY}.json"`; `self._data = read_cache(self.cache_path)`; `self._worker = None`; `self._tier = ""`; `self._backoff_until: float = 0.0`; **`self.status_label` 생성**(레이아웃 배치는 서브클래스 책임); `self._refresh_timer` 생성(미시작)+timeout→`self.refresh`; aboutToQuit→`_shutdown_worker`. 캐시 유무에 따라 status 텍스트 설정("갱신: ..." / "데이터 없음 — 우클릭 → 새로고침"). **`_render()`는 호출하지 않음** — 서브클래스가 UI 구축 후 스스로 호출.
  - 훅(서브클래스 구현): `_make_worker(self) -> QtCore.QThread` (NotImplementedError), `_render(self) -> None` (NotImplementedError), `_apply_responsive(self) -> None` (기본 no-op).
  - `settings` 프로퍼티: `self.store.data[self.CONFIG_KEY]`.
  - `refresh(self, force: bool = False) -> None`: 워커 동작 중이면 return; `not force and time.monotonic() < self._backoff_until`이면 return; `_make_worker()` 생성·시그널 연결(finished_ok→`_on_fetch_ok`, failed→`_on_fetch_failed`)·start.
  - `_on_fetch_ok(self, data: dict)`: `self._data = data`; `write_cache`; status "갱신: {fetched_at[:16]}"; `_render()`.
  - `_on_fetch_failed(self, msg: str)`: status "갱신 실패 — 캐시 표시 중"; `setToolTip(msg)`; `"429" in msg`이면 `self._backoff_until = time.monotonic() + 2 * 60 * 60`.
  - `showEvent`: 타이머 start(`settings.get("refresh_minutes", 30)`분); `_skip_initial_fetch` 아니면 `QtCore.QTimer.singleShot(self._initial_delay_ms(), self.refresh)`.
  - `_initial_delay_ms(self) -> int`: `random.randint(0, 15000)` (모듈 함수로 분리해 테스트 가능하게 — `remote_widget.initial_jitter_ms()`).
  - `hideEvent`: 타이머 stop. `_shutdown_worker`: isRunning이면 `wait(2000)`.
  - `current_tier(self) -> str`: `TIERS`가 None이면 `""`, 아니면 `resolve_breakpoint(self.height(), self.TIERS)`.
  - `on_resized`: TIERS 있고 tier 변화 시 `self._tier` 갱신은 `_render()` 내부 관례 유지 위해 — 비교 후 변화면 `_render()`, 아니면 `_apply_responsive()`.
  - `paintEvent`: 공통 라운드 흰 배경(기존 4벌과 동일 코드).

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_remote_widget.py`:
```python
import time

from PySide6 import QtCore, QtWidgets

from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.core.remote_widget import RemoteWidget, initial_jitter_ms


class _StubWorker(QtCore.QObject):
    """QThread 대체 스텁: start를 기록만 한다."""

    finished_ok = QtCore.Signal(dict)
    failed = QtCore.Signal(str)

    def __init__(self):
        super().__init__()
        self.started = 0

    def isRunning(self):
        return False

    def start(self):
        self.started += 1

    def wait(self, ms):
        self.waited = ms
        return True


class _Concrete(RemoteWidget):
    CONFIG_KEY = "weather"  # 기존 config 기본값 재사용
    TIERS = [(0, "small"), (300, "big")]

    def __init__(self, store):
        super().__init__(store)
        self.render_calls = 0
        self.content_layout.addWidget(self.status_label)
        self._render()

    def _make_worker(self):
        self.last_worker = _StubWorker()
        return self.last_worker

    def _render(self):
        self.render_calls += 1
        self._tier = self.current_tier()


def make(qtbot, tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    store.data["weather"]["_skip_initial_fetch"] = True
    w = _Concrete(store)
    qtbot.addWidget(w)
    return store, w


def test_cache_path_and_empty_status(qtbot, tmp_path):
    store, w = make(qtbot, tmp_path)
    assert w.cache_path.name == "weather.json"
    assert "데이터 없음" in w.status_label.text()


def test_fetch_ok_writes_cache_and_renders(qtbot, tmp_path):
    store, w = make(qtbot, tmp_path)
    before = w.render_calls
    w._on_fetch_ok({"fetched_at": "2026-07-02T10:00:00", "x": 1})
    assert w.cache_path.exists()
    assert "갱신: 2026-07-02T10:00" in w.status_label.text()
    assert w.render_calls == before + 1


def test_429_sets_backoff_and_blocks_auto_refresh(qtbot, tmp_path):
    store, w = make(qtbot, tmp_path)
    w._on_fetch_failed("HTTP Error 429: Too Many Requests")
    assert w._backoff_until > time.monotonic()
    w.refresh()  # 자동 — 백오프에 막힘
    assert not hasattr(w, "last_worker")
    w.refresh(force=True)  # 수동 — 우회
    assert w.last_worker.started == 1


def test_non_429_failure_no_backoff(qtbot, tmp_path):
    store, w = make(qtbot, tmp_path)
    w._on_fetch_failed("timeout")
    assert w._backoff_until == 0.0
    assert w.toolTip() == "timeout"


def test_tier_change_rerenders_on_resize(qtbot, tmp_path):
    store, w = make(qtbot, tmp_path)
    w.resize(220, 200)
    w._render()
    before = w.render_calls
    w.resize(220, 400)  # small → big
    assert w.render_calls == before + 1


def test_initial_jitter_bounds():
    for _ in range(50):
        v = initial_jitter_ms()
        assert 0 <= v <= 15000


def test_shutdown_waits_running_worker(qtbot, tmp_path):
    store, w = make(qtbot, tmp_path)

    class Fake:
        def isRunning(self):
            return True

        def wait(self, ms):
            self.waited = ms

    fake = Fake()
    w._worker = fake
    w._shutdown_worker()
    assert fake.waited == 2000
```

- [ ] **Step 2: RED 확인** — `.venv/Scripts/python.exe -m pytest tests/test_remote_widget.py -v` → ModuleNotFoundError

- [ ] **Step 3: 구현**

`src/teacher_widgets/core/remote_widget.py`:
```python
"""외부 데이터 위젯 공통 베이스.

시간표·주간계획·급식·날씨가 공유하던 수명주기(캐시 로드, showEvent
타이머+지터 fetch, hideEvent 정지, 종료 시 bounded wait, 429 백오프)를
한곳에 모은다. 서브클래스는 CONFIG_KEY·TIERS·_make_worker·_render만 구현.
"""

from __future__ import annotations

import random
import time
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from .base_widget import BaseWidget
from .config_store import ConfigStore
from .data_remote import read_cache, write_cache
from .responsive import resolve_breakpoint

_BACKOFF_SECONDS = 2 * 60 * 60  # 429(할당량 소진) 시 2시간 자동 fetch 중지


def initial_jitter_ms() -> int:
    """시작 fetch 지터(0~15초) — 다수 PC 동시 부팅 버스트 완화."""
    return random.randint(0, 15000)


class RemoteWidget(BaseWidget):
    CONFIG_KEY: str = ""
    TIERS: list | None = None

    def __init__(self, store: ConfigStore):
        super().__init__(self.CONFIG_KEY, store)
        self.cache_path = Path(store.path).parent / "cache" / f"{self.CONFIG_KEY}.json"
        self._data: dict | None = read_cache(self.cache_path)
        self._worker = None
        self._tier = ""
        self._backoff_until: float = 0.0

        self.status_label = QtWidgets.QLabel("", alignment=QtCore.Qt.AlignCenter)
        self.status_label.setStyleSheet("color:#999;")
        if self._data is not None:
            self.status_label.setText(f"갱신: {self._data.get('fetched_at', '')[:16]}")
        else:
            self.status_label.setText("데이터 없음 — 우클릭 → 새로고침")

        self._refresh_timer = QtCore.QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh)

        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._shutdown_worker)

    # --- 서브클래스 훅 ---
    def _make_worker(self):
        raise NotImplementedError

    def _render(self) -> None:
        raise NotImplementedError

    def _apply_responsive(self) -> None:  # 기본 no-op
        pass

    @property
    def settings(self) -> dict:
        return self.store.data[self.CONFIG_KEY]

    # --- 수명주기 ---
    def showEvent(self, event) -> None:
        super().showEvent(event)
        minutes = int(self.settings.get("refresh_minutes", 30))
        self._refresh_timer.start(minutes * 60 * 1000)
        if not self.settings.get("_skip_initial_fetch", False):
            QtCore.QTimer.singleShot(initial_jitter_ms(), self.refresh)

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._refresh_timer.stop()

    def _shutdown_worker(self) -> None:
        worker = self._worker
        if worker is not None and worker.isRunning():
            worker.wait(2000)

    # --- fetch ---
    def refresh(self, force: bool = False) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        if not force and time.monotonic() < self._backoff_until:
            return
        self._worker = self._make_worker()
        self._worker.finished_ok.connect(self._on_fetch_ok)
        self._worker.failed.connect(self._on_fetch_failed)
        self._worker.start()

    def _on_fetch_ok(self, data: dict) -> None:
        self._data = data
        write_cache(self.cache_path, data)
        self.status_label.setText(f"갱신: {data.get('fetched_at', '')[:16]}")
        self._render()

    def _on_fetch_failed(self, msg: str) -> None:
        self.status_label.setText("갱신 실패 — 캐시 표시 중")
        self.setToolTip(msg)
        if "429" in msg:
            self._backoff_until = time.monotonic() + _BACKOFF_SECONDS

    # --- tier / 반응형 ---
    def current_tier(self) -> str:
        if self.TIERS is None:
            return ""
        return resolve_breakpoint(self.height(), self.TIERS)

    def on_resized(self, width: int, height: int) -> None:
        if self.TIERS is not None and self.current_tier() != self._tier:
            self._render()
        else:
            self._apply_responsive()

    # --- 공통 외형 ---
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(QtGui.QColor(255, 255, 255, 235))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 16, 16)
```

- [ ] **Step 4: GREEN + 전체 스위트** — 143 passed 예상 (136+7).

- [ ] **Step 5: 커밋**

```bash
git add src/teacher_widgets/core/remote_widget.py tests/test_remote_widget.py
git commit -m "feat: RemoteWidget 공통 베이스(수명주기·429백오프·시작지터)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: 시간표·주간계획 마이그레이션

**Files:**
- Modify: `src/teacher_widgets/widgets/timetable.py`, `src/teacher_widgets/widgets/weekly_plan.py`
- Test: 기존 테스트 무수정 통과가 검증 기준 (`tests/test_timetable.py`, `tests/test_weekly_plan.py`)

**Interfaces:**
- Consumes: Task 1의 RemoteWidget.
- Produces: 두 위젯이 RemoteWidget 상속. 공개 표면(테스트 참조) 불변.

- [ ] **Step 1: timetable.py 마이그레이션**

변경 내용(정확히):
1. import에 `from teacher_widgets.core.remote_widget import RemoteWidget` 추가. 더 이상 직접 쓰지 않는 import 제거(`read_cache`/`write_cache`는 RemoteWidget이 담당 — timetable에서 직접 사용 없어지면 제거).
2. 클래스 선언: `class TimetableWidget(RemoteWidget):` + 클래스 속성 `CONFIG_KEY = "timetable"`, `TIERS = None`, `BASE_SIZE = (340, 330)`.
3. `__init__(self, store)`: `super().__init__(store)` 호출로 교체(자동으로 cache/status/timer/aboutToQuit 처리). 이후 기존 UI 구축(header_label, grid 생성, `_cells`)과 `self._web_proc = None` 유지. **`self.status_label`은 super가 만들었으므로 생성 코드 삭제, content_layout 배치만 유지.** 캐시 로드/상태 설정/타이머 생성/aboutToQuit 연결 코드 삭제. 말미의 `render_grid()` 호출 유지(초기 렌더).
4. 삭제할 메서드(RemoteWidget이 제공): `showEvent`, `hideEvent`, `_shutdown_worker`, `paintEvent`, `_on_fetch_ok`, `_on_fetch_failed`, `refresh`.
5. 추가:
```python
    def _make_worker(self):
        return FetchWorker(self.settings, self)

    def _render(self) -> None:
        self.render_grid()
```
6. `apply_data(self, data)`는 테스트가 호출 — 유지하되 내부를 RemoteWidget 흐름과 일치시킴:
```python
    def apply_data(self, data: dict) -> None:
        self._data = data
        from teacher_widgets.core.data_remote import write_cache
        write_cache(self.cache_path, data)
        self.render_grid()
```
   (모듈 상단 import 유지가 더 깔끔하면 상단 import로.)
7. `_custom_menu_actions`의 "새로고침"은 `lambda: self.refresh(force=True)`로 (수동 우회).
8. `render_grid` 내부의 `self._tier` 관련 코드는 timetable에 원래 없음 — 무변경. `_apply_responsive`/`on_resized`는 유지하되, RemoteWidget의 on_resized(TIERS=None → `_apply_responsive()`)와 동일 동작이므로 **timetable의 `on_resized` 삭제** 가능 — 삭제.

- [ ] **Step 2: weekly_plan.py 마이그레이션**

동일 요령:
1. `class WeeklyPlanWidget(RemoteWidget):`, `CONFIG_KEY = "weekly_plan"`, `TIERS = PLAN_TIERS`, `BASE_SIZE = (320, 360)`.
2. `__init__`: `super().__init__(store)` 후 UI 구축 + status_label 배치 + `self._web_proc = None` + 말미 `self.render_plan()`. 캐시/타이머/aboutToQuit/상태 코드 삭제.
3. 삭제: `showEvent/hideEvent/_shutdown_worker/paintEvent/_on_fetch_ok/_on_fetch_failed/refresh/current_tier/on_resized` (RemoteWidget 제공; current_tier는 TIERS로 동일 동작).
4. 추가:
```python
    def _make_worker(self):
        return PlanFetchWorker(self.settings, self)

    def _render(self) -> None:
        self.render_plan()
```
5. `apply_data` 유지(테스트 없음이면 삭제 가능 — test_weekly_plan.py는 apply_data 미사용 → **삭제**). `render_plan`은 기존대로 `self._tier = self.current_tier()` 설정 — 유지(on_resized 비교와 맞물림).
6. "새로고침" 메뉴 → `lambda: self.refresh(force=True)`.

- [ ] **Step 3: 두 테스트 파일 무수정 통과 확인**

Run: `.venv/Scripts/python.exe -m pytest tests/test_timetable.py tests/test_weekly_plan.py -v`
Expected: 33개 전부 통과, **테스트 파일 diff 없음**.

- [ ] **Step 4: 전체 스위트** — 143 passed 유지.

- [ ] **Step 5: 커밋**

```bash
git add src/teacher_widgets/widgets/timetable.py src/teacher_widgets/widgets/weekly_plan.py
git commit -m "refactor: 시간표·주간계획을 RemoteWidget 상속으로 이관

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: 급식·날씨 마이그레이션 + 스모크

**Files:**
- Modify: `src/teacher_widgets/widgets/meal.py`, `src/teacher_widgets/widgets/weather.py`
- Test: 기존 테스트 무수정 통과 (`tests/test_meal.py`, `tests/test_weather.py`)

- [ ] **Step 1: meal.py 마이그레이션**

1. `class MealWidget(RemoteWidget):`, `CONFIG_KEY = "meal"`, `TIERS = MEAL_TIERS`, `BASE_SIZE = (240, 300)`.
2. `__init__`: `super().__init__(store)` 후 UI 구축(header/body) + status_label 배치 + 말미 `self.render_meal()`.
3. 삭제: `showEvent/hideEvent/_shutdown_worker/paintEvent/_on_fetch_ok/_on_fetch_failed/refresh/current_tier/on_resized`.
4. 추가: `_make_worker` → `MealFetchWorker(self.settings, self)`, `_render` → `self.render_meal()`.
5. "새로고침" → `force=True`. `render_meal`의 `self._tier = self.current_tier()` 유지.
6. 주의: `test_meal_widget_renders_today`가 `meal_mod.datetime.date`를 몽키패치 — `render_meal` 내부 `datetime.date.today()` 모듈 속성 접근 유지.

- [ ] **Step 2: weather.py 마이그레이션**

동일 요령: `CONFIG_KEY = "weather"`, `TIERS = WEATHER_TIERS`, `BASE_SIZE = (220, 240)`; `_make_worker` → `WeatherFetchWorker(self.settings, self)`; `_render` → `self.render_weather()`; 중복 메서드 삭제; "새로고침" force.

- [ ] **Step 3: 전체 스위트 (테스트 무수정)** — 143 passed.

- [ ] **Step 4: 실측 스모크 (경량 — 위젯 2종 1회)**

Run (offscreen, 지터 있으므로 20초 대기):
```bash
QT_QPA_PLATFORM=offscreen PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "
import sys, tempfile, os; sys.path.insert(0, 'src')
from PySide6 import QtWidgets, QtCore
app = QtWidgets.QApplication([])
from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.widgets.weather import WeatherWidget
from teacher_widgets.widgets.meal import MealWidget
d = tempfile.mkdtemp(); s = ConfigStore(os.path.join(d, 'c.json')); s.load()
ws = [WeatherWidget(s), MealWidget(s)]
for w in ws: w.show()
def check():
    for w in ws: print(w.widget_name, '|', w.status_label.text())
    app.quit()
QtCore.QTimer.singleShot(25000, check)
app.exec()
"
```
Expected: 두 위젯 모두 `갱신: ...` (지터 0~15초 후 fetch → 25초면 충분).

- [ ] **Step 5: 커밋**

```bash
git add src/teacher_widgets/widgets/meal.py src/teacher_widgets/widgets/weather.py
git commit -m "refactor: 급식·날씨를 RemoteWidget 상속으로 이관

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 자기 점검 (Self-Review)

**1. 커버리지:** RemoteWidget 추출(리뷰 지시 항목 전부 — 상태·수명주기·refresh 훅·render 훅·캐시·tier 스켈레톤) → Task 1 ✅ / 429 백오프+force 우회 → Task 1 ✅ / 시작 지터 → Task 1 ✅ / 4위젯 이관·동작보존 → Task 2·3 ✅ / 실측 확인 → Task 3 ✅
**2. 플레이스홀더:** 없음. 마이그레이션 단계는 삭제 목록+추가 코드 명시 ✅
**3. 타입 일관성:** `refresh(force=False)`, `_make_worker()->QThread`, `_render()`, `settings->dict`, `initial_jitter_ms()->int` — Task 간 일치 ✅
**리스크 노트:** 기존 테스트 중 `_on_fetch_failed("timeout")` 직접 호출(툴팁 검증)은 RemoteWidget 구현과 동일 동작 ✅. weekly_plan의 `test_plan_widget_tier_from_height`는 current_tier가 RemoteWidget로 이동해도 동작 동일 ✅.
