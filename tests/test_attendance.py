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
    build_attendance_workbook,
    months_with_records,
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


def test_parse_no_space_input():
    assert parse_command("7번 6월29일결석", TODAY) == {
        "number": 7, "date": "2026-06-29", "status": "결석", "reason": "질병"}


def test_parse_failures():
    assert parse_command("결석", TODAY) is None            # 번호 없음
    assert parse_command("7번", TODAY) is None             # 출결어 없음
    assert parse_command("7번 낮잠", TODAY) is None        # 미지의 단어
    assert parse_command("", TODAY) is None


def _sample_data():
    data = {}
    set_record(data, "2026-07-03", 7, "결석", "질병")
    set_record(data, "2026-07-15", 51, "결석", "출석인정")
    set_record(data, "2026-06-29", 7, "지각", "질병")
    return data


def test_months_with_records():
    assert months_with_records(_sample_data()) == ["2026-06", "2026-07"]
    assert months_with_records({}) == []


def test_workbook_single_month():
    wb = build_attendance_workbook(_sample_data(), [7, 51], ["2026-07"])
    assert wb.sheetnames == ["2026-07"]
    ws = wb["2026-07"]
    assert "2026년 7월" in ws.cell(row=1, column=1).value
    assert "♡" in ws.cell(row=2, column=1).value  # 범례
    assert ws.cell(row=4, column=1).value == "번호"
    assert ws.cell(row=4, column=32).value == 31  # 7월 말일
    # 5행=번호7, 6행=번호51; 날짜 d는 열 d+1
    assert ws.cell(row=5, column=1).value == 7
    assert ws.cell(row=5, column=4).value == "♡"    # 7/3
    assert ws.cell(row=6, column=16).value == "△"   # 51번 7/15
    assert ws.cell(row=5, column=5).value in (None, "")


def test_workbook_multi_month_and_weekend_fill():
    wb = build_attendance_workbook(_sample_data(), [7], ["2026-06", "2026-07"])
    assert wb.sheetnames == ["2026-06", "2026-07"]
    ws = wb["2026-07"]
    # 2026-07-04는 토요일 → 헤더 열 5 회색 채움
    assert ws.cell(row=4, column=5).fill.start_color.rgb.endswith("DDDDDD")
    # 평일(7/3 금) 헤더는 채움 없음(기본 00000000)
    assert not str(ws.cell(row=4, column=4).fill.start_color.rgb).endswith("DDDDDD")


import json as _json

from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.widgets.attendance import AttendanceWidget


def make_widget(qtbot, tmp_path, boys=3, girls=2):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    store.set_roster(boys, girls)
    w = AttendanceWidget(store)
    qtbot.addWidget(w)
    return store, w


def test_widget_table_shape_from_roster(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path)  # 번호 1,2,3,51,52
    assert w.widget_name == "attendance"
    assert w.table.rowCount() == 5
    nums = [int(w.table.verticalHeaderItem(r).text()) for r in range(5)]
    assert nums == [1, 2, 3, 51, 52]


def test_apply_record_updates_cell_and_file(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path)
    date_iso = f"{w._year:04d}-{w._month:02d}-03"
    w.apply_record(2, date_iso, "결석", "질병")
    assert w.cell_symbol(2, 3) == "♡"
    saved = _json.loads((tmp_path / "attendance.json").read_text(encoding="utf-8"))
    assert saved["records"][date_iso]["2"]["status"] == "결석"
    w.apply_clear(2, date_iso)
    assert w.cell_symbol(2, 3) == ""


def test_handle_command_with_explicit_date(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path)
    assert w.handle_command_text(f"3번 {w._month}월 5일 체험학습") is True
    assert w.cell_symbol(3, 5) == "△"


def test_handle_command_today_confirm(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path)
    w._confirm_today = lambda: True  # 팝업 우회
    import datetime as _dt
    today = _dt.date.today()
    w._year, w._month = today.year, today.month
    w.rebuild_table()
    assert w.handle_command_text("51번 결석") is True
    assert w.cell_symbol(51, today.day) == "♡"


def test_handle_command_rejects_unknown_number_and_garbage(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path)
    assert w.handle_command_text("9번 결석") is False   # roster 밖(1-3,51-52)
    assert w.error_label.text() != ""
    assert w.handle_command_text("염소") is False


def test_month_navigation(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path)
    w._year, w._month = 2026, 1
    w.rebuild_table()
    assert w.table.columnCount() == 31
    w.go_month(1)   # 2월
    assert (w._year, w._month) == (2026, 2)
    assert w.table.columnCount() == 28
    w.go_month(-2)  # 12월로 롤백
    assert (w._year, w._month) == (2025, 12)


def test_shrunk_roster_does_not_crash(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path)  # 1,2,3,51,52
    date_iso = f"{w._year:04d}-{w._month:02d}-03"
    w.apply_record(51, date_iso, "결석", "질병")
    store.set_roster(3, 0)  # 여학생 제거 — 51 사라짐
    assert w.cell_symbol(51, 3) == ""      # 크래시 없이 빈 값
    w.apply_record(2, date_iso, "결석", "질병")  # _refresh_cell 경로도 안전
    w.rebuild_table()
    assert w.table.rowCount() == 3


def test_show_event_rebuilds_to_current_roster(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path)
    store.set_roster(2, 0)
    w.show()  # showEvent → rebuild_table
    assert w.table.rowCount() == 2
