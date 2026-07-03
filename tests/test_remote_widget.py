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
    w.show()  # resizeEvent는 offscreen 플랫폼에서 show() 없이는 전달되지 않음
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
