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
