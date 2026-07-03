import datetime

from teacher_widgets.widgets.attendance import (
    STATUSES,
    REASONS,
    SYMBOLS,
    symbol_for,
    set_record,
    clear_record,
    get_record,
    month_symbols,
    parse_command,
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


TODAY = datetime.date(2026, 7, 3)


def test_parse_full_command():
    assert parse_command("7번 6월 29일 결석", TODAY) == {
        "number": 7, "date": "2026-06-29", "status": "결석", "reason": "질병"}


def test_parse_no_date_returns_none_date():
    assert parse_command("5번 체험학습", TODAY) == {
        "number": 5, "date": None, "status": "결석", "reason": "출석인정"}


def test_parse_slash_and_dot_dates():
    assert parse_command("12번 7/1 미인정지각", TODAY)["date"] == "2026-07-01"
    assert parse_command("12번 7.1 미인정지각", TODAY)["status"] == "지각"
    assert parse_command("12번 7/1 미인정지각", TODAY)["reason"] == "미인정"


def test_parse_prefix_modifiers():
    assert parse_command("3번 인정조퇴", TODAY) == {
        "number": 3, "date": None, "status": "조퇴", "reason": "출석인정"}
    assert parse_command("3번 기타결과", TODAY)["reason"] == "기타"
    assert parse_command("3번 질병결석", TODAY)["reason"] == "질병"


def test_parse_clear():
    assert parse_command("7번 6월 29일 취소", TODAY) == {
        "number": 7, "date": "2026-06-29", "clear": True}
    assert parse_command("7번 지우기", TODAY) == {
        "number": 7, "date": None, "clear": True}


def test_parse_ref_year():
    assert parse_command("7번 1월 5일 결석", TODAY, ref_year=2027)["date"] == "2027-01-05"


def test_parse_failures():
    assert parse_command("결석", TODAY) is None            # 번호 없음
    assert parse_command("7번", TODAY) is None             # 출결어 없음
    assert parse_command("7번 낮잠", TODAY) is None        # 미지의 단어
    assert parse_command("", TODAY) is None
