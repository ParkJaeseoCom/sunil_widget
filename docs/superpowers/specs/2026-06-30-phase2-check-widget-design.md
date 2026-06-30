# Phase 2 — 체크 위젯 설계 문서

- 작성일: 2026-06-30
- 상위 설계: [2026-06-29-teacher-desktop-widgets-design.md](2026-06-29-teacher-desktop-widgets-design.md) §6(위젯 7: 체크), §11
- 범위: Phase 2의 **로컬형 대표 위젯 = 체크 위젯**. (외부형 대표 = 시간표는 Firestore 직접 읽기 방식으로 별도 진행)

## 1. 목표

번호별 체크박스로 숙제·과제·제출 여부 등을 점검하는 로컬 위젯. 출결 위젯과 **학급 구성(남 N·여 M)을 공유**한다. 외부 의존 없음 — 완전 로컬.

## 2. 공유 학급 구성 (class_roster)

- `config.json`에 최상위 `class_roster: { "boys": N, "girls": M }` 추가. 체크 위젯과 향후 출결 위젯이 공유.
- **번호 생성 규칙:** 남 = `1 .. boys`, 여 = `51 .. 50+girls`. (예: boys=14, girls=14 → 1~14, 51~64, 합 28)
- **기본값:** `{ "boys": 14, "girls": 14 }`.
- **설정 방법:** 위젯 우클릭 메뉴 → "학급 구성 설정" → 작은 다이얼로그(남/여 인원 스핀박스). 저장 시 모든 체크 위젯의 번호 그리드가 갱신된다.

## 3. 체크 동작

- 번호별 체크박스 = **이진(체크/해제)**. "했는지 안 했는지".
- 상단 **제출 카운트**: "제출 X/전체" (전체 = boys+girls, X = 체크된 수).
- 하단 **초기화** 버튼: 모든 체크 해제 + 저장.
- 번호 그리드는 3열 정도로 배치(레퍼런스 role_check와 유사), 반응형으로 폰트/간격 조정.

## 4. 제목(용도)

- 편집 가능한 제목(기본 "체크"). 우클릭 메뉴 → "제목 변경" → 입력 다이얼로그. config에 저장. 예: "숙제 검사", "우유 확인".

## 5. 다중 인스턴스

- 메모와 같은 **고정 풀(pool)** 방식: `checklist`, `checklist_1`, `checklist_2`, `checklist_3` (최대 4개). 각자 제목·체크 상태 독립.
- 트레이 메뉴에서 각 인스턴스를 on/off. 기본은 `checklist` 1개만 표시.
- (동적 무제한 추가는 향후 개선 사항으로 남김 — Phase 1 메모와 동일한 패턴으로 일관성 유지.)

## 6. 데이터 모델 (config.json)

```json
"class_roster": { "boys": 14, "girls": 14 },
"checklists": {
  "checklist":   { "title": "체크",     "checked": [3, 7, 51] },
  "checklist_1": { "title": "숙제 검사", "checked": [] }
}
```
- `checked`는 체크된 번호 목록(정수 배열). 위젯 visible·geometry는 기존 `widgets` 슬롯 그대로 사용.

## 7. 컴포넌트 구조

- **`core/roster.py`** (순수): `roster_numbers(boys, girls) -> list[int]` — `[1..boys] + [51..50+girls]`.
- **`core/config_store.py`** (확장): `class_roster` 기본값 + `get_roster() -> (boys, girls)` / `set_roster(boys, girls)`.
- **`core/base_widget.py`** (확장): 컨텍스트 메뉴 확장 훅 `_custom_menu_actions(menu) -> dict[QAction, Callable]` (기본 빈 dict). 서브클래스가 자기 메뉴 항목을 잠금/닫기 위에 추가.
- **`widgets/checklist.py`**: 체크 상태 헬퍼(`get_title`/`set_title`/`get_checked`/`set_checked`/`toggle`) + `RosterDialog`(남/여 인원) + `TitleDialog` + `ChecklistWidget(BaseWidget)`.
- **`tray.py` / `main.py`** (확장): checklist 풀(4개) 등록, 기본 `checklist` 표시.

## 8. 반응형·공통

- BaseWidget 상속으로 이동·**리사이즈**·멀티모니터·숨기기·불투명도·위치저장 자동.
- `on_resized`에서 번호 버튼 폰트/그리드 간격을 반응형 스케일로 조정.

## 9. 에러 처리·엣지

- 학급 구성 변경 시 기존 `checked` 목록 중 새 번호 범위를 벗어난 값은 표시에서 제외(데이터는 보존하되 그리드엔 유효 번호만 렌더). 인원 축소 후 복원 시 데이터 유지.
- boys/girls는 0 이상, 합 30 이하 정도로 입력 제한(스핀박스 범위).
- 다중 인스턴스는 인스턴스별 상태로 완전 독립(공유 상태 없음).

## 10. 테스트 전략

- `roster_numbers` 순수 함수: 경계·기본·여 시작 51 검증.
- config_store: `get_roster`/`set_roster` 라운드트립 + 기본값.
- checklist 헬퍼: title·checked 라운드트립, toggle, 인스턴스 독립성.
- ChecklistWidget(qtbot): 그리드가 roster 번호대로 생성, 체크 시 카운트 갱신, 초기화로 전부 해제, 제목 반영, roster 변경 시 그리드 재생성.
- base_widget: `_custom_menu_actions` 훅이 기존 잠금/닫기 동작을 깨지 않음(기존 4테스트 유지).

## 11. 범위 밖(후속)
- 시간표 위젯(Firestore 직접 읽기) — 체크 완료 후 별도 spec.
- 체크 인스턴스 동적 무제한 추가, 학급 구성의 전역 설정 UI(트레이) — 향후.
