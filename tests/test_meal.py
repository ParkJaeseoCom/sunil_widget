import json

from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.widgets.meal import (
    build_meal_url,
    parse_meal_response,
    split_allergy,
    MEAL_TIERS,
    MealWidget,
)


def test_build_meal_url_without_key():
    url = build_meal_url("B10", "7031170", "20260629", "20260703")
    assert "mealServiceDietInfo" in url
    assert "ATPT_OFCDC_SC_CODE=B10" in url
    assert "SD_SCHUL_CODE=7031170" in url
    assert "MLSV_FROM_YMD=20260629" in url and "MLSV_TO_YMD=20260703" in url
    assert "KEY=" not in url


def test_build_meal_url_with_key():
    assert "KEY=abc123" in build_meal_url("B10", "7031170", "20260629", "20260703", "abc123")


def test_split_allergy():
    assert split_allergy("햄프씨드떡갈비 (2.4.5.6.10.12.15.16)") == ("햄프씨드떡갈비", "2.4.5.6.10.12.15.16")
    assert split_allergy("들기름김 ") == ("들기름김", "")
    assert split_allergy("깍두기* (9)") == ("깍두기*", "9")


SAMPLE = {"mealServiceDietInfo": [
    {"head": [{"list_total_count": 2}]},
    {"row": [
        {"MLSV_YMD": "20260702", "MMEAL_SC_NM": "중식",
         "DDISH_NM": "퀴노아찹쌀밥 <br/>햄프씨드떡갈비 (2.4.5)<br/>깍두기* (9)",
         "CAL_INFO": "641.5 Kcal"},
        {"MLSV_YMD": "20260703", "MMEAL_SC_NM": "중식",
         "DDISH_NM": "현미밥 <br/>미역국 (5)", "CAL_INFO": "600 Kcal"},
    ]},
]}

EMPTY = {"RESULT": {"CODE": "INFO-200", "MESSAGE": "해당하는 데이터가 없습니다."}}


def test_parse_meal_response():
    meals = parse_meal_response(SAMPLE)
    assert len(meals) == 2
    first = meals[0]
    assert first["date"] == "20260702"
    assert first["cal"] == "641.5 Kcal"
    assert first["menu"][0] == {"name": "퀴노아찹쌀밥", "allergy": ""}
    assert first["menu"][1] == {"name": "햄프씨드떡갈비", "allergy": "2.4.5"}


def test_parse_meal_response_empty_and_garbage():
    assert parse_meal_response(EMPTY) == []
    assert parse_meal_response({}) == []


def test_meal_tiers():
    assert MEAL_TIERS == [(0, "today"), (420, "week")]


MEAL_CACHE = {
    "fetched_at": "2026-07-02T07:00:00",
    "meals": [
        {"date": "20260702", "cal": "641.5 Kcal",
         "menu": [{"name": "퀴노아찹쌀밥", "allergy": ""},
                  {"name": "햄프씨드떡갈비", "allergy": "2.4.5"}]},
    ],
}


def make_meal_widget(qtbot, tmp_path, cache=MEAL_CACHE):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    store.data["meal"]["_skip_initial_fetch"] = True
    if cache is not None:
        p = tmp_path / "cache" / "meal.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    w = MealWidget(store)
    qtbot.addWidget(w)
    return store, w


def test_meal_widget_renders_today(qtbot, tmp_path, monkeypatch):
    import datetime as dt

    class FakeDate(dt.date):
        @classmethod
        def today(cls):
            return cls(2026, 7, 2)

    from teacher_widgets.widgets import meal as meal_mod
    monkeypatch.setattr(meal_mod.datetime, "date", FakeDate)
    store, w = make_meal_widget(qtbot, tmp_path)
    w.render_meal()
    text = w.menu_text()
    assert "퀴노아찹쌀밥" in text
    assert "641.5" in text


def test_meal_widget_no_data_message(qtbot, tmp_path):
    store, w = make_meal_widget(qtbot, tmp_path, cache={"fetched_at": "x", "meals": []})
    w.render_meal()
    assert "급식 정보가 없습니다" in w.menu_text()
