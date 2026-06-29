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


# ---------------------------------------------------------------------------
# Fix 3: 완료(finished) 상태에서 시작 버튼 동작
# ---------------------------------------------------------------------------

def test_toggle_from_finished_state_resets_and_starts(qtbot, tmp_path):
    """finished 상태에서 _toggle() 호출 → 리셋 후 시작, 버튼=일시정지."""
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    w = TimerWidget(store)
    qtbot.addWidget(w)

    # 모델을 finished 상태로 수동 조작
    w.model.state = "finished"
    w.model.remaining = 0

    w._toggle()

    # 리셋 후 시작했으므로 running 상태여야 함
    assert w.model.state == "running"
    assert w.start_btn.text() == "일시정지"
    # remaining 은 initial(_initial) 로 복원된 후 start() 됐으므로 > 0
    assert w.model.remaining > 0


def test_toggle_from_finished_label_is_not_lying(qtbot, tmp_path):
    """finished 상태에서 _toggle() 호출 후 버튼 텍스트와 모델 상태가 일관성을 가진다.

    '일시정지' 라고 표시되었는데 모델은 idle/finished 인 상황이 없어야 함.
    """
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    w = TimerWidget(store)
    qtbot.addWidget(w)

    w.model.state = "finished"
    w.model.remaining = 0
    w._toggle()

    btn_text = w.start_btn.text()
    if btn_text == "일시정지":
        assert w.model.state == "running"
    else:
        assert btn_text == "시작"
        assert w.model.state in ("idle", "paused", "finished")


def test_toggle_from_idle_with_zero_remaining_stays_start(qtbot, tmp_path):
    """remaining==0 인 idle 상태에서 _toggle() → 모델이 running 이 되지 않으므로 버튼=시작."""
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    w = TimerWidget(store)
    qtbot.addWidget(w)

    # idle + remaining=0 (set_duration(0,0) 사용)
    w.model.set_duration(0, 0)
    assert w.model.state == "idle"
    assert w.model.remaining == 0

    w._toggle()

    # start() 는 remaining==0 이면 no-op → state 는 여전히 idle
    assert w.model.state == "idle"
    # 버튼은 "일시정지" 가 아니어야 함 (거짓말 금지)
    assert w.start_btn.text() == "시작"
