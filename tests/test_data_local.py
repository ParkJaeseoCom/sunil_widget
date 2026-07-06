import json

from teacher_widgets.core.data_local import (
    load_json_with_backup,
    save_json_with_backup,
)


def test_load_missing_returns_empty(tmp_path):
    assert load_json_with_backup(tmp_path / "a.json") == {}


def test_save_then_load_roundtrip_and_bak(tmp_path):
    p = tmp_path / "d" / "a.json"
    save_json_with_backup(p, {"v": 1})       # 최초 저장(부모 생성, bak 없음)
    assert not (tmp_path / "d" / "a.json.bak").exists()
    save_json_with_backup(p, {"v": 2})       # 두 번째 저장 → 이전본이 bak
    assert load_json_with_backup(p) == {"v": 2}
    assert json.loads((tmp_path / "d" / "a.json.bak").read_text(encoding="utf-8")) == {"v": 1}
    assert not list((tmp_path / "d").glob("*.tmp"))  # 임시 파일 잔존 없음(원자적 교체)


def test_corrupt_recovers_from_bak(tmp_path):
    p = tmp_path / "a.json"
    save_json_with_backup(p, {"v": 1})
    save_json_with_backup(p, {"v": 2})
    p.write_text("{broken", encoding="utf-8")
    assert load_json_with_backup(p) == {"v": 1}  # bak 복구


def test_corrupt_without_bak_preserves_and_returns_empty(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("{broken", encoding="utf-8")
    assert load_json_with_backup(p) == {}
    corrupts = list(tmp_path.glob("a.corrupt-*.json"))
    assert len(corrupts) == 1
    assert corrupts[0].read_text(encoding="utf-8") == "{broken"
