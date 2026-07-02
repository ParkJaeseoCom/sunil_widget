import datetime
import json

from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.widgets.weekly_plan import (
    week_monday,
    build_schedules_query,
    parse_schedule_docs,
    parse_messages_doc,
    group_entries,
    pick_days,
    PLAN_TIERS,
    WeeklyPlanWidget,
)


def _doc(date, dept, content, order=None):
    fields = {
        "date": {"stringValue": date},
        "department": {"stringValue": dept},
        "content": {"stringValue": content},
    }
    if order is not None:
        fields["order"] = {"integerValue": str(order)}
    return {"name": f"doc-{date}-{dept}", "fields": fields}


def test_week_monday_weekday_and_weekend():
    assert week_monday(datetime.date(2026, 7, 2)) == datetime.date(2026, 6, 29)  # 목
    assert week_monday(datetime.date(2026, 7, 4)) == datetime.date(2026, 7, 6)   # 토→다음주 월
    assert week_monday(datetime.date(2026, 7, 5)) == datetime.date(2026, 7, 6)   # 일→다음주 월


def test_build_schedules_query_shape():
    q = build_schedules_query("2026-06-29", "2026-07-06")
    assert q["from"] == [{"collectionId": "schedules"}]
    filters = q["where"]["compositeFilter"]["filters"]
    assert filters[0]["fieldFilter"]["op"] == "GREATER_THAN_OR_EQUAL"
    assert filters[0]["fieldFilter"]["value"]["stringValue"] == "2026-06-29"
    assert filters[1]["fieldFilter"]["op"] == "LESS_THAN_OR_EQUAL"
    assert q["limit"] == 200


def test_parse_schedule_docs():
    docs = [_doc("2026-06-29", "행정실", "체육관 사용 안내", 5),
            _doc("2026-06-29", "학사일정", "기말평가주간")]
    out = parse_schedule_docs(docs)
    assert out[0] == {"date": "2026-06-29", "department": "행정실",
                      "content": "체육관 사용 안내", "order": 5}
    assert out[1]["order"] == 0


def test_parse_messages_doc():
    doc = {"fields": {"principal": {"stringValue": "안전 제일"},
                      "vicePrincipal": {"stringValue": "수고 많으십시다"}}}
    assert parse_messages_doc(doc) == {"principal": "안전 제일",
                                       "vicePrincipal": "수고 많으십시다"}
    assert parse_messages_doc(None) == {"principal": "", "vicePrincipal": ""}
    assert parse_messages_doc({}) == {"principal": "", "vicePrincipal": ""}


def test_group_entries_hakssa_first_then_order():
    entries = [
        {"date": "2026-06-29", "department": "행정실", "content": "b", "order": 1},
        {"date": "2026-06-29", "department": "학사일정", "content": "a", "order": 99},
        {"date": "2026-06-29", "department": "교육과정부", "content": "c", "order": 0},
        {"date": "2026-06-30", "department": "5학년", "content": "d", "order": 0},
    ]
    g = group_entries(entries)
    assert [e["content"] for e in g["2026-06-29"]] == ["a", "c", "b"]
    assert [e["content"] for e in g["2026-06-30"]] == ["d"]


def test_pick_days_tiers():
    mon = datetime.date(2026, 6, 29)
    thu = datetime.date(2026, 7, 2)
    assert pick_days("compact", mon, thu) == [thu]
    assert pick_days("two_days", mon, thu) == [thu, datetime.date(2026, 7, 3)]
    week = pick_days("week", mon, thu)
    assert week[0] == mon and week[-1] == datetime.date(2026, 7, 6) and len(week) == 6


def test_pick_days_weekend_uses_base_monday():
    sat = datetime.date(2026, 7, 4)
    mon = week_monday(sat)  # 2026-07-06
    assert pick_days("compact", mon, sat) == [mon]


def test_plan_tiers_shape():
    assert PLAN_TIERS == [(0, "compact"), (300, "two_days"), (480, "week")]


PLAN_CACHE = {
    "fetched_at": "2026-07-02T10:00:00",
    "week_monday": "2026-06-29",
    "entries": [
        {"date": "2026-07-02", "department": "학사일정", "content": "기말평가주간", "order": 0},
        {"date": "2026-07-02", "department": "행정실", "content": "체육관 공사", "order": 1},
        {"date": "2026-07-03", "department": "5학년", "content": "진단검사", "order": 0},
    ],
    "messages": {"principal": "안전 제일", "vicePrincipal": ""},
}


def make_plan_widget(qtbot, tmp_path, cache=PLAN_CACHE):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    store.data["weekly_plan"]["_skip_initial_fetch"] = True
    if cache is not None:
        p = tmp_path / "cache" / "weekly_plan.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    w = WeeklyPlanWidget(store)
    qtbot.addWidget(w)
    return store, w


def test_plan_widget_renders_cache(qtbot, tmp_path):
    store, w = make_plan_widget(qtbot, tmp_path)
    assert w.widget_name == "weekly_plan"
    text = w.days_text()  # 렌더된 전체 텍스트 요약 접근자
    assert "기말평가주간" in text


def test_plan_widget_no_cache_empty_state(qtbot, tmp_path):
    store, w = make_plan_widget(qtbot, tmp_path, cache=None)
    assert "데이터 없음" in w.status_label.text() or "새로고침" in w.status_label.text()


def test_plan_widget_tier_from_height(qtbot, tmp_path):
    store, w = make_plan_widget(qtbot, tmp_path)
    w.resize(320, 200)
    assert w.current_tier() == "compact"
    w.resize(320, 350)
    assert w.current_tier() == "two_days"
    w.resize(320, 600)
    assert w.current_tier() == "week"


def test_plan_widget_hakssa_badge_precedes(qtbot, tmp_path):
    store, w = make_plan_widget(qtbot, tmp_path)
    w.resize(320, 600)
    w.render_plan()
    text = w.days_text()
    assert text.index("기말평가주간") < text.index("체육관 공사")
