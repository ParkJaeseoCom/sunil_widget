import json

from PySide6 import QtWidgets

from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.widgets import timetable as tt_mod
from teacher_widgets.widgets.timetable import (
    parse_global_state,
    filter_lessons,
    cell_text,
    derive_targets,
    build_app_command,
    TargetDialog,
    TimetableWidget,
    DAYS,
    PERIODS,
)

TARGETS = {"class": ["1-진", "1-선"], "room": ["체육관"], "teacher": ["컴퓨터"]}


def _fs_lesson(name, teacher, room, class_id, day, period):
    return {"mapValue": {"fields": {
        "name": {"stringValue": name},
        "teacher": {"stringValue": teacher},
        "room": {"stringValue": room},
        "classId": {"stringValue": class_id},
        "day": {"stringValue": day},
        "period": {"integerValue": str(period)},
        "color": {"stringValue": "bg-red-100"},
    }}}


def _fs_doc(active_id, tables):
    return {"fields": {
        "activeTableId": {"stringValue": active_id},
        "updatedAt": {"integerValue": "123"},
        "timetables": {"arrayValue": {"values": [
            {"mapValue": {"fields": {
                "id": {"stringValue": tid},
                "name": {"stringValue": tname},
                "lessons": {"arrayValue": {"values": lessons}},
            }}}
            for tid, tname, lessons in tables
        ]}},
    }}


SAMPLE = _fs_doc("t2", [
    ("t1", "옛 시간표", [_fs_lesson("과학", "담임", "과학실", "3-진", "화", 2)]),
    ("t2", "2026 기본 시간표", [
        _fs_lesson("국어", "담임", "교실", "1-진", "월", 1),
        _fs_lesson("체육", "1-3학년 체육", "체육관", "1-진", "월", 2),
        _fs_lesson("영어", "1/2학년 영어R", "A어학실", "1-선", "월", 1),
        _fs_lesson("음악", "1-3학년 음악", "음악실", "1-진", "화", 1),
    ]),
])


def test_constants():
    assert DAYS == ["월", "화", "수", "목", "금"]
    assert PERIODS == [1, 2, 3, 4, 5, 6, 7]


def test_parse_selects_active_table():
    out = parse_global_state(SAMPLE)
    assert out["table_name"] == "2026 기본 시간표"
    assert len(out["lessons"]) == 4
    first = out["lessons"][0]
    assert first == {"name": "국어", "teacher": "담임", "room": "교실",
                     "classId": "1-진", "day": "월", "period": 1}


def test_parse_falls_back_to_first_table():
    doc = _fs_doc("없는ID", [("t1", "유일", [_fs_lesson("수학", "담임", "교실", "2-미", "수", 3)])])
    out = parse_global_state(doc)
    assert out["table_name"] == "유일"
    assert out["lessons"][0]["period"] == 3


def test_parse_empty_doc():
    assert parse_global_state({}) == {"table_name": "", "lessons": []}


def test_filter_lessons_by_class():
    lessons = parse_global_state(SAMPLE)["lessons"]
    grid = filter_lessons(lessons, "class", "1-진")
    assert set(grid.keys()) == {("월", 1), ("월", 2), ("화", 1)}
    assert grid[("월", 1)][0]["name"] == "국어"


def test_filter_lessons_by_room_and_teacher():
    lessons = parse_global_state(SAMPLE)["lessons"]
    assert list(filter_lessons(lessons, "room", "체육관"))[0] == ("월", 2)
    assert list(filter_lessons(lessons, "teacher", "1/2학년 영어R"))[0] == ("월", 1)


def test_cell_text_class_view_shows_special_room():
    entries = [{"name": "체육", "room": "체육관", "classId": "1-진"}]
    assert cell_text(entries, "class") == "체육📍체육관"
    entries2 = [{"name": "국어", "room": "교실", "classId": "1-진"}]
    assert cell_text(entries2, "class") == "국어"


def test_cell_text_other_views_show_class_and_merge():
    entries = [
        {"name": "영어", "room": "A어학실", "classId": "1-선"},
        {"name": "영어", "room": "A어학실", "classId": "1-진"},
    ]
    assert cell_text(entries, "room") == "1-선/1-진"
    assert cell_text([], "class") == ""


def test_cell_text_overflow():
    entries = [{"name": f"과목{i}", "room": "교실", "classId": f"{i}-진"} for i in range(5)]
    text = cell_text(entries, "class")
    assert "외 2" in text


def test_derive_targets_sorted_unique():
    lessons = parse_global_state(SAMPLE)["lessons"]
    targets = derive_targets(lessons)
    assert targets["class"] == ["1-선", "1-진"]
    assert "체육관" in targets["room"]
    assert "1-3학년 체육" in targets["teacher"]


def test_target_dialog_initial_state(qtbot):
    dlg = TargetDialog(TARGETS, "class", "1-선")
    qtbot.addWidget(dlg)
    assert dlg.class_radio.isChecked()
    assert dlg.target_combo.currentText() == "1-선"
    assert dlg.values() == ("class", "1-선")


def test_target_dialog_switch_type_repopulates(qtbot):
    dlg = TargetDialog(TARGETS, "class", "1-진")
    qtbot.addWidget(dlg)
    dlg.room_radio.setChecked(True)
    items = [dlg.target_combo.itemText(i) for i in range(dlg.target_combo.count())]
    assert items == ["체육관"]
    assert dlg.values() == ("room", "체육관")


def test_target_dialog_unknown_target_defaults_first(qtbot):
    dlg = TargetDialog(TARGETS, "class", "9-없음")
    qtbot.addWidget(dlg)
    assert dlg.values() == ("class", "1-진")


CACHE_DATA = {
    "fetched_at": "2026-07-02T10:00:00",
    "table_name": "2026 기본 시간표",
    "lessons": [
        {"name": "국어", "teacher": "담임", "room": "교실",
         "classId": "1-진", "day": "월", "period": 1},
        {"name": "체육", "teacher": "1-3학년 체육", "room": "체육관",
         "classId": "1-진", "day": "화", "period": 2},
    ],
}


def make_widget(qtbot, tmp_path, cache=CACHE_DATA):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    store.data["timetable"]["_skip_initial_fetch"] = True
    if cache is not None:
        cache_file = tmp_path / "cache" / "timetable.json"
        cache_file.parent.mkdir(parents=True)
        cache_file.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    w = TimetableWidget(store)
    qtbot.addWidget(w)
    return store, w


def test_widget_loads_cache_and_renders(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path)
    assert w.widget_name == "timetable"
    assert "1-진" in w.header_label.text()
    assert w._cells[("월", 1)].text() == "국어"
    assert w._cells[("화", 2)].text() == "체육📍체육관"
    assert w._cells[("금", 7)].text() == ""


def test_widget_without_cache_shows_empty_state(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path, cache=None)
    assert "새로고침" in w.status_label.text() or "데이터 없음" in w.status_label.text()


def test_apply_data_writes_cache_and_rerenders(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path, cache=None)
    w.apply_data(CACHE_DATA)
    assert w._cells[("월", 1)].text() == "국어"
    saved = json.loads((tmp_path / "cache" / "timetable.json").read_text(encoding="utf-8"))
    assert saved["table_name"] == "2026 기본 시간표"


def test_change_target_updates_config_and_grid(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path)
    # 다이얼로그 우회: 내부 상태 직접 적용 경로 검증
    w._set_target("room", "체육관")
    assert store.data["timetable"]["view_type"] == "room"
    assert store.data["timetable"]["target"] == "체육관"
    assert w._cells[("화", 2)].text() == "1-진"


def test_fetch_failed_sets_status(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path)
    w._on_fetch_failed("timeout")
    assert "갱신 실패" in w.status_label.text()
    assert w.toolTip() == "timeout"


class _FakeRunningWorker:
    """isRunning()=True 인 워커를 흉내내며 wait() 호출을 기록."""

    def __init__(self):
        self.wait_calls: list[int] = []

    def isRunning(self) -> bool:
        return True

    def wait(self, ms: int) -> bool:
        self.wait_calls.append(ms)
        return True


def test_shutdown_worker_waits_bounded_when_running(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path)
    fake = _FakeRunningWorker()
    w._worker = fake
    w._shutdown_worker()
    assert fake.wait_calls == [2000]


def test_shutdown_worker_noop_when_no_worker(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path)
    w._worker = None
    w._shutdown_worker()  # 예외 없이 통과해야 함


def test_shutdown_worker_connected_to_about_to_quit(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path)
    app = QtWidgets.QApplication.instance()
    fake = _FakeRunningWorker()
    w._worker = fake
    app.aboutToQuit.emit()
    assert fake.wait_calls == [2000]


# ---------------------------------------------------------------------------
# Fix 2: 숨김 상태에서는 fetch 타이머가 돌지 않아야 한다
# ---------------------------------------------------------------------------

def test_refresh_timer_not_started_until_shown(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path)
    assert w._refresh_timer.isActive() is False


def test_show_starts_timer_and_hide_stops_it(qtbot, tmp_path):
    store, w = make_widget(qtbot, tmp_path)
    w.show()
    assert w._refresh_timer.isActive() is True
    w.hide()
    assert w._refresh_timer.isActive() is False


def test_build_app_command_prefers_edge(monkeypatch):
    monkeypatch.setattr(tt_mod.shutil, "which",
                        lambda exe: r"C:\edge\msedge.exe" if exe == "msedge" else None)
    cmd = build_app_command("https://example.com/")
    assert cmd == [r"C:\edge\msedge.exe", "--app=https://example.com/"]


def test_build_app_command_falls_back_to_chrome(monkeypatch):
    monkeypatch.setattr(tt_mod.shutil, "which",
                        lambda exe: r"C:\chrome\chrome.exe" if exe == "chrome" else None)
    cmd = build_app_command("https://example.com/")
    assert cmd[0].endswith("chrome.exe")


def test_build_app_command_none_when_no_browser(monkeypatch):
    monkeypatch.setattr(tt_mod.shutil, "which", lambda exe: None)
    assert build_app_command("https://example.com/") is None
