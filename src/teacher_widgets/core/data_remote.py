"""외부 데이터 공용 토대: Firebase 익명 인증 · Firestore REST GET · 로컬 캐시.

stdlib(urllib)만 사용한다 — 배포본에 의존성을 추가하지 않기 위함.
HTTP 함수는 얇게 유지하고 테스트하지 않는다(파싱·캐시는 순수 함수로 테스트).
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path


def anon_sign_in(api_key: str, timeout: int = 15) -> str:
    """Firebase Identity Toolkit 익명 로그인 → idToken 반환."""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={api_key}"
    req = urllib.request.Request(
        url,
        data=json.dumps({"returnSecureToken": True}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)["idToken"]


def firestore_get_document(
    project_id: str, doc_path: str, id_token: str, timeout: int = 30
) -> dict:
    """Firestore REST로 문서 1개 GET (Firestore JSON 형식 그대로 반환)."""
    url = (
        f"https://firestore.googleapis.com/v1/projects/{project_id}"
        f"/databases/(default)/documents/{doc_path}"
    )
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {id_token}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def read_cache(path: Path) -> dict | None:
    """캐시 JSON 로드. 없거나 손상 시 None."""
    path = Path(path)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def write_cache(path: Path, data: dict) -> None:
    """캐시 JSON 저장. 부모 폴더 자동 생성."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
