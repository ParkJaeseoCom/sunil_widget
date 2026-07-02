from teacher_widgets.core.data_remote import read_cache, write_cache


def test_cache_roundtrip(tmp_path):
    path = tmp_path / "cache" / "timetable.json"  # 부모 폴더 없음 → 자동 생성 확인
    data = {
        "fetched_at": "2026-07-02T10:00:00",
        "table_name": "2026 기본 시간표",
        "lessons": [
            {"name": "국어", "teacher": "담임", "room": "교실",
             "classId": "1-진", "day": "월", "period": 1}
        ],
    }
    write_cache(path, data)
    assert read_cache(path) == data


def test_read_cache_missing_returns_none(tmp_path):
    assert read_cache(tmp_path / "nope.json") is None


def test_read_cache_corrupt_returns_none(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    assert read_cache(path) is None
