from PySide6 import QtWidgets

from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.widgets.checklist import (
    ChecklistWidget,
    RosterDialog,
    TitleDialog,
    get_title,
    set_title,
    get_checked,
    set_checked,
    toggle,
)


def make_store(tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    return store


def test_title_default_and_roundtrip(tmp_path):
    store = make_store(tmp_path)
    assert get_title(store, "checklist") == "체크"
    set_title(store, "checklist", "숙제 검사")
    assert get_title(store, "checklist") == "숙제 검사"


def test_checked_roundtrip_sorted(tmp_path):
    store = make_store(tmp_path)
    assert get_checked(store, "checklist") == set()
    set_checked(store, "checklist", {7, 3, 51})
    assert get_checked(store, "checklist") == {3, 7, 51}
    # 저장은 정렬된 list
    assert store.data["checklists"]["checklist"]["checked"] == [3, 7, 51]


def test_toggle_adds_then_removes(tmp_path):
    store = make_store(tmp_path)
    assert toggle(store, "checklist", 5) is True
    assert get_checked(store, "checklist") == {5}
    assert toggle(store, "checklist", 5) is False
    assert get_checked(store, "checklist") == set()


def test_instances_are_independent(tmp_path):
    store = make_store(tmp_path)
    set_checked(store, "checklist", {1})
    set_checked(store, "checklist_1", {51})
    assert get_checked(store, "checklist") == {1}
    assert get_checked(store, "checklist_1") == {51}


def test_roster_dialog_returns_values(qtbot):
    dlg = RosterDialog(10, 12)
    qtbot.addWidget(dlg)
    assert dlg.values() == (10, 12)
    dlg.boys_spin.setValue(8)
    dlg.girls_spin.setValue(9)
    assert dlg.values() == (8, 9)


def test_roster_dialog_clamps_range(qtbot):
    dlg = RosterDialog(0, 0)
    qtbot.addWidget(dlg)
    dlg.boys_spin.setValue(999)  # 최대 30으로 클램프
    assert dlg.values()[0] == 30


def test_title_dialog_returns_value(qtbot):
    dlg = TitleDialog("숙제")
    qtbot.addWidget(dlg)
    assert dlg.value() == "숙제"
    dlg.edit.setText("우유 확인")
    assert dlg.value() == "우유 확인"


def test_widget_builds_grid_from_roster(qtbot, tmp_path):
    store = make_store(tmp_path)
    store.set_roster(3, 2)  # 1,2,3,51,52
    w = ChecklistWidget(store, "checklist")
    qtbot.addWidget(w)
    assert sorted(w._buttons.keys()) == [1, 2, 3, 51, 52]


def test_widget_toggle_updates_count_and_config(qtbot, tmp_path):
    store = make_store(tmp_path)
    store.set_roster(3, 0)
    w = ChecklistWidget(store, "checklist")
    qtbot.addWidget(w)
    assert "0/3" in w.count_label.text()
    w._on_toggle(2)
    assert "1/3" in w.count_label.text()
    assert 2 in store.data["checklists"]["checklist"]["checked"]


def test_widget_reset_clears_all(qtbot, tmp_path):
    store = make_store(tmp_path)
    store.set_roster(3, 0)
    w = ChecklistWidget(store, "checklist")
    qtbot.addWidget(w)
    w._on_toggle(1)
    w._on_toggle(2)
    w.reset()
    assert "0/3" in w.count_label.text()
    assert store.data["checklists"]["checklist"]["checked"] == []


def test_widget_title_from_config(qtbot, tmp_path):
    store = make_store(tmp_path)
    set_title(store, "checklist", "숙제 검사")
    w = ChecklistWidget(store, "checklist")
    qtbot.addWidget(w)
    assert w.title_label.text() == "숙제 검사"


def test_widget_change_roster_rebuilds_grid(qtbot, tmp_path):
    store = make_store(tmp_path)
    store.set_roster(2, 0)
    w = ChecklistWidget(store, "checklist")
    qtbot.addWidget(w)
    assert sorted(w._buttons.keys()) == [1, 2]
    # roster 변경을 직접 적용(다이얼로그 우회)
    store.set_roster(2, 1)
    store.save()
    w.rebuild_grid()
    assert sorted(w._buttons.keys()) == [1, 2, 51]


def test_widget_name_passed_to_base(qtbot, tmp_path):
    store = make_store(tmp_path)
    w = ChecklistWidget(store, "checklist_2")
    qtbot.addWidget(w)
    assert w.widget_name == "checklist_2"
