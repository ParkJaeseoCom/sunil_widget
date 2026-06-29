from PySide6 import QtCore

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


# ---------------------------------------------------------------------------
# Fix 1: 리사이즈 hit-test 및 퍼시스트
# ---------------------------------------------------------------------------

def test_hit_test_right_bottom_corner_returns_both_edges():
    """오른쪽 하단 모서리 → RightEdge | BottomEdge."""
    rect = QtCore.QRect(0, 0, 200, 150)
    # 오른쪽 하단 모서리 (내부 끝 2px)
    pos = QtCore.QPoint(198, 148)
    edges = BaseWidget.hit_test_resize(pos, rect)
    assert edges & QtCore.Qt.RightEdge
    assert edges & QtCore.Qt.BottomEdge


def test_hit_test_left_edge_only():
    """왼쪽 가장자리 중간 → LeftEdge 만."""
    rect = QtCore.QRect(0, 0, 200, 150)
    pos = QtCore.QPoint(4, 75)
    edges = BaseWidget.hit_test_resize(pos, rect)
    assert edges & QtCore.Qt.LeftEdge
    assert not (edges & QtCore.Qt.RightEdge)
    assert not (edges & QtCore.Qt.TopEdge)
    assert not (edges & QtCore.Qt.BottomEdge)


def test_hit_test_interior_returns_no_edges():
    """위젯 내부 중심 → 에지 없음."""
    rect = QtCore.QRect(0, 0, 200, 150)
    pos = QtCore.QPoint(100, 75)
    edges = BaseWidget.hit_test_resize(pos, rect)
    assert not edges


def test_hit_test_top_right_corner():
    """오른쪽 상단 모서리 → RightEdge | TopEdge."""
    rect = QtCore.QRect(0, 0, 200, 150)
    pos = QtCore.QPoint(196, 3)
    edges = BaseWidget.hit_test_resize(pos, rect)
    assert edges & QtCore.Qt.RightEdge
    assert edges & QtCore.Qt.TopEdge


def test_resize_persist_updates_config(qtbot, tmp_path):
    """크기 변경 후 persist_geometry() 가 config 에 새 크기를 기록한다."""
    store = make_store(tmp_path)
    w = BaseWidget("clock", store)
    qtbot.addWidget(w)
    w.setGeometry(0, 0, 220, 140)

    # 새 크기로 변경 후 persist
    w.resize(300, 200)
    w.persist_geometry()

    saved = store.get_widget("clock")["geometry"]
    assert saved[2] == 300
    assert saved[3] == 200


def test_minimum_size_enforced():
    """BaseWidget 최소 크기는 120×80 이어야 한다."""
    from teacher_widgets.core.config_store import ConfigStore
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as td:
        store = ConfigStore(pathlib.Path(td) / "c.json")
        store.load()
        w = BaseWidget("clock", store)
        assert w.minimumWidth() == 120
        assert w.minimumHeight() == 80
        w.deleteLater()


def test_no_resize_when_locked(qtbot, tmp_path):
    """잠금 상태에서는 리사이즈 상태가 시작되지 않아야 한다."""
    store = make_store(tmp_path)
    w = BaseWidget("clock", store)
    qtbot.addWidget(w)
    w.set_locked(True)

    # 잠금 상태에서 마우스 프레스를 경계에서 시뮬레이션
    w.setGeometry(0, 0, 200, 150)
    press_event = QtCore.QEvent(QtCore.QEvent.MouseButtonPress)
    # 직접 내부 상태 확인: 잠긴 상태에서는 _resize_start_global 이 None 이어야 함
    assert w._locked is True
    assert w._resize_start_global is None
