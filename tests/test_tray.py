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


# ---------------------------------------------------------------------------
# Fix 2: tray check-state 동기화 (aboutToShow)
# ---------------------------------------------------------------------------

def test_tray_refresh_unchecks_when_hidden_via_config(qtbot, tmp_path):
    """위젯이 config 에서 visible=False 로 바뀐 뒤 aboutToShow 가 발생하면
    트레이 액션 체크박스가 False 로 갱신되어야 한다."""
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    store.set_widget_visible("clock", True)
    reg = WidgetRegistry(store)
    reg.register("clock", lambda: BaseWidget("clock", store))
    menu = build_tray_menu(reg)

    clock_action = next(a for a in menu.actions() if a.text() == "clock")
    assert clock_action.isChecked() is True  # 빌드 시점에 True

    # 외부에서 visible=False 로 변경 (hide_to_config 경로)
    store.set_widget_visible("clock", False)

    # aboutToShow 신호를 수동으로 발생시켜 refresh 실행
    menu.aboutToShow.emit()

    assert clock_action.isChecked() is False


def test_tray_refresh_does_not_trigger_show_hide(qtbot, tmp_path):
    """aboutToShow 로 인한 setChecked 가 show/hide 핸들러를 재실행하지 않아야 한다."""
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    store.set_widget_visible("clock", True)
    reg = WidgetRegistry(store)

    show_hide_calls = []

    def factory():
        w = BaseWidget("clock", store)
        return w

    reg.register("clock", factory)
    menu = build_tray_menu(reg)

    # toggled 신호가 추가로 발생하는지 감시
    clock_action = next(a for a in menu.actions() if a.text() == "clock")
    clock_action.toggled.connect(lambda checked: show_hide_calls.append(checked))

    # config 를 False 로 바꾸고 refresh
    store.set_widget_visible("clock", False)
    menu.aboutToShow.emit()

    # setChecked 가 blockSignals 로 보호되므로 toggled 핸들러가 호출되면 안 됨
    assert show_hide_calls == []


def test_tray_refresh_checks_when_shown_via_config(qtbot, tmp_path):
    """처음에 visible=False 인 위젯이 config 에서 True 로 바뀌면 refresh 후 체크가 된다."""
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    store.set_widget_visible("clock", False)
    reg = WidgetRegistry(store)
    reg.register("clock", lambda: BaseWidget("clock", store))
    menu = build_tray_menu(reg)

    clock_action = next(a for a in menu.actions() if a.text() == "clock")
    assert clock_action.isChecked() is False

    store.set_widget_visible("clock", True)
    menu.aboutToShow.emit()

    assert clock_action.isChecked() is True


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


def test_tray_menu_lists_attendance(qtbot, tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    reg = WidgetRegistry(store)
    reg.register("attendance", lambda: BaseWidget("attendance", store))
    menu = build_tray_menu(reg)
    assert "attendance" in [a.text() for a in menu.actions() if a.text()]
