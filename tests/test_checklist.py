from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.widgets.checklist import (
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
