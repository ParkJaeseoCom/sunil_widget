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
