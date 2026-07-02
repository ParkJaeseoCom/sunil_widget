"""외부 데이터 공용 토대: Firebase 익명 인증 · Firestore REST GET · 로컬 캐시.

stdlib(urllib)만 사용한다 — 배포본에 의존성을 추가하지 않기 위함.
HTTP 함수는 얇게 유지하고 테스트하지 않는다(파싱·캐시는 순수 함수로 테스트).
"""

from __future__ import annotations

import json
import ssl
import urllib.request
from pathlib import Path

_CTX: ssl.SSLContext | None = None


def _ssl_context() -> ssl.SSLContext:
    """공용 SSL 컨텍스트: 체인 검증은 유지하되 X509 strict만 해제.

    Python 3.13+ 기본 VERIFY_X509_STRICT가 나이스 등 정부 인증서
    (Authority Key Identifier 누락)를 거부하는 문제의 우회.
    """
    global _CTX
    if _CTX is None:
        _CTX = ssl.create_default_context()
        _CTX.verify_flags &= ~ssl.VERIFY_X509_STRICT
    return _CTX


def http_get_json(url: str, headers: dict | None = None, timeout: int = 20) -> dict:
    """공용 GET(JSON). 정부 API 대응 컨텍스트 사용."""
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as r:
        return json.load(r)


def _rows_to_documents(rows: list) -> list[dict]:
    """runQuery 응답 행에서 document만 추출(순수 — 테스트 대상)."""
    return [row["document"] for row in rows if "document" in row]


def firestore_run_query(
    project_id: str,
    parent_path: str,
    structured_query: dict,
    id_token: str,
    timeout: int = 30,
) -> list[dict]:
    """Firestore REST :runQuery — document 행만 반환."""
    url = (
        f"https://firestore.googleapis.com/v1/projects/{project_id}"
        f"/databases/(default)/documents/{parent_path}:runQuery"
    )
    req = urllib.request.Request(
        url,
        data=json.dumps({"structuredQuery": structured_query}).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {id_token}",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as r:
        return _rows_to_documents(json.load(r))


def anon_sign_in(api_key: str, timeout: int = 15) -> str:
    """Firebase Identity Toolkit 익명 로그인 → idToken 반환."""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={api_key}"
    req = urllib.request.Request(
        url,
        data=json.dumps({"returnSecureToken": True}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as r:
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
    with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as r:
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
