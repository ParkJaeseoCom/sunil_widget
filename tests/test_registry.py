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
