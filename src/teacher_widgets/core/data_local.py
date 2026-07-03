"""로컬 민감 데이터 파일 I/O: .bak 1세대 백업과 손상 복구.

출결·상담기록 등 학생 관련 데이터가 사용하는 공용 저장 계층.
이 모듈은 네트워크를 절대 사용하지 않는다.
"""

from __future__ import annotations

import datetime
import json
import shutil
from pathlib import Path


def load_json_with_backup(path: Path) -> dict:
    """JSON 로드. 손상 시 .bak 복구, 실패 시 손상본 보존 후 빈 dict."""
    path = Path(path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    bak = path.with_suffix(path.suffix + ".bak")
    if bak.exists():
        try:
            return json.loads(bak.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    # 복구 불가 — 데이터 소실 방지를 위해 손상본을 보존하고 빈 데이터로 시작
    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    corrupt = path.with_name(f"{path.stem}.corrupt-{ts}{path.suffix}")
    try:
        path.rename(corrupt)
    except OSError:
        pass
    return {}


def save_json_with_backup(path: Path, data: dict) -> None:
    """저장 전 기존 파일을 .bak으로 복사(1세대 백업)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
