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
