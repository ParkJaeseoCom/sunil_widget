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
