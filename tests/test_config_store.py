import json
from pathlib import Path

from teacher_widgets.core.config_store import ConfigStore, deep_merge, DEFAULT_CONFIG


def test_deep_merge_overrides_nested():
    base = {"a": 1, "b": {"c": 2, "d": 3}}
    override = {"b": {"c": 99}}
    result = deep_merge(base, override)
    assert result == {"a": 1, "b": {"c": 99, "d": 3}}
    assert base == {"a": 1, "b": {"c": 2, "d": 3}}
    assert override == {"b": {"c": 99}}


def test_load_missing_file_returns_defaults(tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    data = store.load()
    assert data["widget_opacity"] == DEFAULT_CONFIG["widget_opacity"]


def test_save_then_reload_roundtrip(tmp_path):
    path = tmp_path / "config.json"
    store = ConfigStore(path)
    store.load()
    store.set_widget_visible("clock", False)
    store.set_widget_geometry("clock", [10, 20, 200, 120])
    store.save()

    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["widgets"]["clock"] == {"visible": False, "geometry": [10, 20, 200, 120]}


def test_get_widget_unknown_returns_default_geometry(tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    w = store.get_widget("memo_3")
    # 미기록 위젯은 기본 숨김 — 첫 실행 '시계만 표시' 보장
    assert w["visible"] is False
    assert len(w["geometry"]) == 4


def test_opacity_get_set(tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    store.set_opacity(80)
    assert store.get_opacity() == 80


def test_get_widget_returns_isolated_copy(tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    store.set_widget_visible("clock", True)
    w = store.get_widget("clock")
    w["visible"] = False
    assert store.get_widget("clock")["visible"] is True


def test_default_roster(tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    assert store.get_roster() == (14, 14)


def test_set_roster_roundtrip(tmp_path):
    path = tmp_path / "config.json"
    store = ConfigStore(path)
    store.load()
    store.set_roster(10, 12)
    assert store.get_roster() == (10, 12)
    store.save()

    reloaded = ConfigStore(path)
    reloaded.load()
    assert reloaded.get_roster() == (10, 12)


def test_default_timetable_settings(tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    tt = store.data["timetable"]
    assert tt["view_type"] == "class"
    assert tt["target"] == "1-진"
    assert tt["project_id"] == "sunil-time-table"
    assert tt["refresh_minutes"] == 60
