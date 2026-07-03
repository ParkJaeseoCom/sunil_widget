from teacher_widgets.widgets.attendance import (
    STATUSES,
    REASONS,
    SYMBOLS,
    symbol_for,
    set_record,
    clear_record,
    get_record,
    month_symbols,
)


def test_symbol_table_complete_16():
    assert STATUSES == ["결석", "지각", "조퇴", "결과"]
    assert REASONS == ["질병", "미인정", "기타", "출석인정"]
    assert len(SYMBOLS) == 16
    assert symbol_for("결석", "질병") == "♡"
    assert symbol_for("결석", "출석인정") == "△"  # 체험학습
    assert symbol_for("지각", "미인정") == "X"
    assert symbol_for("조퇴", "기타") == "∽"
    assert symbol_for("결과", "출석인정") == "▽"


def test_set_get_clear_record():
    data = {}
    set_record(data, "2026-07-03", 7, "결석", "질병")
    assert get_record(data, "2026-07-03", 7) == {"status": "결석", "reason": "질병"}
    assert data["records"]["2026-07-03"]["7"]["status"] == "결석"
    set_record(data, "2026-07-03", 7, "결석", "출석인정")  # 덮어쓰기
    assert get_record(data, "2026-07-03", 7)["reason"] == "출석인정"
    clear_record(data, "2026-07-03", 7)
    assert get_record(data, "2026-07-03", 7) is None
    assert "2026-07-03" not in data["records"]  # 빈 날짜 정리


def test_month_symbols():
    data = {}
    set_record(data, "2026-07-03", 7, "결석", "질병")
    set_record(data, "2026-07-15", 51, "지각", "출석인정")
    set_record(data, "2026-08-01", 7, "결석", "질병")  # 다른 달 — 제외
    out = month_symbols(data, 2026, 7)
    assert out == {(7, 3): "♡", (51, 15): "◁"}
