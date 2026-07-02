"""시간표 위젯: Firestore 문서 파싱/필터 순수 함수 + 다이얼로그 + GUI.

이 파일의 상단부(순수 함수)는 Task 2, TargetDialog는 Task 3,
FetchWorker·TimetableWidget은 Task 4~5에서 추가된다.
"""

from __future__ import annotations

DAYS = ["월", "화", "수", "목", "금"]
PERIODS = [1, 2, 3, 4, 5, 6, 7]

_VIEW_KEY = {"class": "classId", "room": "room", "teacher": "teacher"}


def _sv(fields: dict, key: str, default: str = "") -> str:
    return fields.get(key, {}).get("stringValue", default)


def parse_global_state(fs_doc: dict) -> dict:
    """Firestore 문서에서 활성 시간표의 경량 lessons를 추출."""
    fields = fs_doc.get("fields", {})
    active_id = _sv(fields, "activeTableId")
    tables = fields.get("timetables", {}).get("arrayValue", {}).get("values", [])

    chosen = None
    for t in tables:
        tf = t.get("mapValue", {}).get("fields", {})
        if _sv(tf, "id") == active_id:
            chosen = tf
            break
    if chosen is None and tables:
        chosen = tables[0].get("mapValue", {}).get("fields", {})
    if chosen is None:
        return {"table_name": "", "lessons": []}

    lessons = []
    for lv in chosen.get("lessons", {}).get("arrayValue", {}).get("values", []):
        lf = lv.get("mapValue", {}).get("fields", {})
        day = _sv(lf, "day")
        period_raw = lf.get("period", {}).get("integerValue")
        if not day or period_raw is None:
            continue
        lessons.append({
            "name": _sv(lf, "name"),
            "teacher": _sv(lf, "teacher"),
            "room": _sv(lf, "room"),
            "classId": _sv(lf, "classId"),
            "day": day,
            "period": int(period_raw),
        })
    return {"table_name": _sv(chosen, "name"), "lessons": lessons}


def filter_lessons(lessons: list, view_type: str, target: str) -> dict:
    """뷰 유형·대상으로 필터해 {(day, period): [lesson...]} 반환."""
    key = _VIEW_KEY[view_type]
    grid: dict = {}
    for lesson in lessons:
        if lesson.get(key) == target:
            grid.setdefault((lesson["day"], lesson["period"]), []).append(lesson)
    return grid


def cell_text(entries: list, view_type: str) -> str:
    """한 칸의 표시 문자열. 웹앱 표시 규칙 계승."""
    if not entries:
        return ""
    parts = []
    for e in entries[:3]:
        if view_type == "class":
            room = e.get("room", "")
            name = e.get("name", "")
            parts.append(f"{name}📍{room}" if room and room != "교실" else name)
        else:
            parts.append(e.get("classId") or e.get("name", ""))
    text = "/".join(parts)
    if len(entries) > 3:
        text += f" 외 {len(entries) - 3}"
    return text


def derive_targets(lessons: list) -> dict:
    """캐시된 lessons에서 뷰별 대상 목록을 유도(정렬·중복 제거·빈값 제외)."""
    out = {"class": set(), "room": set(), "teacher": set()}
    for lesson in lessons:
        if lesson.get("classId"):
            out["class"].add(lesson["classId"])
        if lesson.get("room"):
            out["room"].add(lesson["room"])
        if lesson.get("teacher"):
            out["teacher"].add(lesson["teacher"])
    return {k: sorted(v) for k, v in out.items()}
