# Phase 4-C — 상담기록 위젯 설계 문서

- 작성일: 2026-07-03
- 상위 설계: [2026-06-29-teacher-desktop-widgets-design.md](2026-06-29-teacher-desktop-widgets-design.md) §6(위젯 6: 상담기록)
- 전제: Phase 4-B 완료(`core/data_local.py` 재사용). 로컬형 — BaseWidget 직접 상속.

## 1. 목표·민감정보 원칙

지도/상담 내용을 **빠르게 타이핑해 두는 누가기록 보조** 위젯 (나이스 입력 전 임시 보관 + 법적 증빙 보조). 각 기록 = **원문(RAW) + 로컬 규칙 정제본 + 자동 타임스탬프** 3요소. **완전 로컬**(counseling.json), 외부 전송·AI 호출 절대 금지.

## 2. 데이터 모델

- 파일: `teacher-widgets-data/counseling.json` — `data_local.load/save_json_with_backup` 사용(.bak·손상 보존 자동).
```json
{ "entries": [ { "ts": "2026-07-03T14:30:00", "raw": "3교시 김OO 복도 뛰어다님 주의", "refined": "3교시 김OO 복도 뛰어다님 주의 관련 지도함." } ] }
```
- `ts`는 기록 시각 자동 부착(초 단위 ISO) — **수정 불가**(증빙 무결성). 항목 삭제는 허용(오입력 대응).

## 3. 정제 규칙 (결정적 — AI 아님)

`refine_text(raw: str) -> str`:
1. 공백 정리(연속 공백/개행 → 한 칸, 양끝 strip).
2. 끝 문장부호(`.`,`!`,`?`, `…`) 제거.
3. 말미가 이미 **"함"으로 끝나면**(예: "…지도함", "…안내함") → `.`만 부착.
4. 그 외 → `" 관련 지도함."` 부착.
- 빈 문자열/공백만 → 빈 문자열 반환(기록 거부용).

## 4. 위젯 UI

- 상단: 제목 "📋 상담·지도 기록" + 건수.
- **입력줄(QLineEdit)** + Enter → 즉시 기록(타임스탬프 자동). 빈 입력 무시.
- **목록(QListWidget)**: 시간 역순. 표시 `MM/DD HH:MM  원문(축약)`. 툴팁 = 정제본 전문. 항목 우클릭 → "정제본 복사"(클립보드 — 나이스 붙여넣기용) / "삭제"(확인 팝업).
- 위젯 우클릭(공통 훅): "Excel 내보내기" (전체).
- 반응형 폰트. BASE_SIZE (300, 340).

## 5. Excel 출력

- `build_counseling_workbook(entries) -> Workbook` (openpyxl — 4-B에서 도입됨): 시트 1개 "상담기록", 헤더 `일시 | 원문 | 정제본`, 시간 역순, 열 너비 지정(가독). 저장은 QFileDialog(얇게).

## 6. 컴포넌트 구조

```
widgets/counseling.py   # refine_text·entry 헬퍼(add/delete/sorted)·Excel 빌더(순수) + CounselingWidget
main.py                 # counseling 등록
```

## 7. 테스트 전략

- 순수: refine_text(공백·문장부호·"함" 말미·빈 입력), add/delete/sorted 헬퍼(ts 자동·역순), Excel 빌더(메모리 워크북 셀 검증).
- 위젯(qtbot): 입력→목록 반영·파일 저장, 삭제(확인 훅 오버라이드), 건수 표시, 빈 입력 무시.
- 네트워크 없음.

## 8. 엣지

- counseling.json 손상 → data_local이 처리(.bak/corrupt 보존).
- 긴 원문 → 목록 축약(60자+…), 툴팁/Excel엔 전문.
- 같은 초에 여러 기록 → 허용(리스트 append 순서 유지).

## 9. 범위 밖

- AI 정제(향후 옵션 구조만 — 기본 off 원칙 유지), 기간 필터 Excel, 항목 수정(무결성 위해 삭제만).
