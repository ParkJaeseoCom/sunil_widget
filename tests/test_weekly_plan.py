import datetime

from teacher_widgets.widgets.weekly_plan import (
    week_monday,
    build_schedules_query,
    parse_schedule_docs,
    parse_messages_doc,
    group_entries,
    pick_days,
    PLAN_TIERS,
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
