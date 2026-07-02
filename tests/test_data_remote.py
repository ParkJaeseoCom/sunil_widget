import ssl

from teacher_widgets.core.data_remote import _ssl_context, _rows_to_documents, read_cache, write_cache


def test_ssl_context_relaxes_strict_only():
    ctx = _ssl_context()
    assert ctx.verify_mode == ssl.CERT_REQUIRED  # 체인 검증은 유지
    assert not (ctx.verify_flags & ssl.VERIFY_X509_STRICT)  # strict만 해제
    assert _ssl_context() is ctx  # 모듈 캐시


def test_rows_to_documents_filters_non_document_rows():
    rows = [
        {"readTime": "..."},  # 문서 없는 메타 행
        {"document": {"name": "d1", "fields": {"date": {"stringValue": "2026-07-02"}}}},
        {"document": {"name": "d2", "fields": {}}},
    ]
    docs = _rows_to_documents(rows)
    assert [d["name"] for d in docs] == ["d1", "d2"]


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
