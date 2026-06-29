from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.widgets.memo import (
    get_memo_text,
    set_memo_text,
    MemoWidget,
)


def test_memo_text_roundtrip(tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    set_memo_text(store, "memo_2", "준비물: 가위, 풀")
    assert get_memo_text(store, "memo_2") == "준비물: 가위, 풀"


def test_get_memo_text_default_empty(tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    assert get_memo_text(store, "memo_9") == ""


def test_memo_widget_loads_saved_text(qtbot, tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    set_memo_text(store, "memo_1", "오늘 회의 3시")
    w = MemoWidget(store, "memo_1")
    qtbot.addWidget(w)
    assert w.widget_name == "memo_1"
    assert w.editor.toPlainText() == "오늘 회의 3시"


def test_memo_widget_saves_on_text_change(qtbot, tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    w = MemoWidget(store, "memo_1")
    qtbot.addWidget(w)
    w.editor.setPlainText("새 메모")
    w._save_text()
    assert get_memo_text(store, "memo_1") == "새 메모"
