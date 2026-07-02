# Phase 2 — 시간표 위젯 설계 문서

- 작성일: 2026-07-02
- 상위 설계: [2026-06-29-teacher-desktop-widgets-design.md](2026-06-29-teacher-desktop-widgets-design.md) §6(위젯 1: 시간표)
- 범위: Phase 2의 **외부형 대표 위젯 = 시간표**. 원설계의 "Vercel 프록시" 대신 **Firestore 직접 읽기(익명 인증)** 로 확정 — 2026-07-02 실측 검증 완료.

## 1. 목표

학교 시간표 시스템(sunil-timetable, Firebase+Vercel)의 시간표를 **읽기 전용**으로 표시한다. 학급/특별실/전담 중 하나를 선택해 해당 뷰를 보여주고, 더블클릭 시 웹앱을 앱 모드 창으로 연다.

## 2. 데이터 소스 (실측 검증됨)

- **인증:** Firebase Identity Toolkit REST 익명 로그인
  `POST https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API_KEY}` → `idToken`
- **문서:** Firestore REST GET (Bearer idToken)
  `projects/sunil-time-table/databases/(default)/documents/artifacts/seonil-timetable-v1/public/data/timetables_state/global_state`
- **문서 구조:** `{ activeTableId, timetables: [{id, name, lessons[], pool[]}], updatedAt }`
- **lesson 필드(확정):** `name(과목)·teacher·room·classId('1-진')·day('월'~'금')·period(1~7, int)·color`, `groupId`(분반, 선택적)
- **크기:** 약 1.1MB (lessons 891개 기준). `pool`은 미배치 과목 — 위젯 불필요.
- **설정값(공개 웹 키 — 배포 안전):**
  - apiKey: `AIzaSyBLatEhyjsQDPNJVO5FWQHPfkdyaTQhrR0`
  - projectId: `sunil-time-table`
  - artifact appId: `seonil-timetable-v1`
  - 웹앱 URL: `https://sunil-timetable.vercel.app/`
- 위 값들은 config.json 기본값으로 두어 변경 가능하게 한다.

## 3. 데이터 흐름

1. 백그라운드 스레드에서: 익명 인증 → 문서 GET → **activeTableId의 시간표에서 lessons만 경량 파싱**.
2. 파싱 결과를 **캐시 파일** `teacher-widgets-data/cache/timetable.json`에 저장 (config.json에 넣지 않음 — 1MB 오염 방지). 캐시 형식: `{ "fetched_at": iso8601, "table_name": str, "lessons": [{name,teacher,room,classId,day,period}, ...] }`.
3. **갱신 시점:** 위젯 시작 시 + 1시간 주기 + 우클릭 메뉴 "새로고침".
4. **실패 처리:** 네트워크/파싱 실패 시 기존 캐시 표시 유지 + 위젯에 "갱신 실패" 표식(작은 라벨). 캐시도 없으면 "데이터 없음 — 새로고침" 안내. GUI 스레드는 절대 블로킹하지 않는다(스레드 → Qt signal로 결과 전달).

## 4. 대상 선택

- config: `timetable: { "view_type": "class"|"room"|"teacher", "target": "1-진", ... }` 기본 `class / 1-진`.
- 우클릭 메뉴(BaseWidget `_custom_menu_actions` 훅) → "대상 변경" 다이얼로그: 유형 라디오(학급/특별실/전담) + 대상 콤보.
- **대상 목록은 캐시된 lessons에서 유도**(classId/room/teacher 고유값 정렬) — 하드코딩 없음. 웹앱 쪽 변경에 자동 적응.
- 필터 규칙(웹앱과 동일): class→`lesson.classId==target`, room→`lesson.room==target`, teacher→`lesson.teacher==target`.

## 5. 표시

- 그리드: 열=월~금(5), 행=1~7교시. 헤더에 요일, 좌측에 교시 번호.
- **오늘 요일 열 강조**(배경 틴트).
- 셀 내용: 과목명. 학급 뷰에서 room≠'교실'이면 `📍room` 병기. room/teacher 뷰에서는 `classId` 병기. 같은 칸 복수 수업은 과목명을 "/"로 병합(최대 3개+`외 N`).
- 상단: 대상 이름(예: "1-진 시간표") + 갱신 상태(마지막 갱신 시각 또는 "갱신 실패").
- 반응형: 기존 `scale_factor`/`scaled_font_pt`로 폰트 조정. BASE_SIZE (340, 330) 내외.

## 6. 클릭 → 웹앱

- **더블클릭** 시 웹앱을 앱 모드로 실행: `msedge --app=https://sunil-timetable.vercel.app/` (Edge는 Windows 11 기본 탑재; 없으면 chrome 시도, 둘 다 없으면 기본 브라우저 `webbrowser.open`).
- 이전에 위젯이 띄운 프로세스가 살아있으면 새로 열지 않고 해당 창을 **맨 앞으로**(Win32 `SetForegroundWindow`, best-effort — 실패해도 무해).

## 7. 컴포넌트 구조

- **`core/data_remote.py`** (신규): 외부 데이터 공용 토대.
  - `anon_sign_in(api_key) -> str` (idToken)
  - `firestore_get_document(project_id, doc_path, id_token) -> dict` (Firestore REST JSON)
  - `read_cache(path) -> dict|None` / `write_cache(path, data) -> None`
  - 순수 stdlib(urllib) 사용 — 의존성 추가 없음.
- **`widgets/timetable.py`** (신규):
  - 순수: `parse_global_state(fs_doc) -> dict` (활성 시간표의 경량 lessons 추출), `filter_lessons(lessons, view_type, target) -> dict[(day,period), list]`, `cell_text(entries, view_type) -> str`, `derive_targets(lessons) -> dict` (유형별 대상 목록)
  - `TargetDialog` (유형 라디오 + 콤보)
  - `FetchWorker` (QThread — 인증+GET+파싱, 시그널로 결과/에러 전달)
  - `TimetableWidget(BaseWidget)` (widget_name="timetable")
- **`main.py`**: `timetable` 등록.

## 8. 테스트 전략

- 순수함수(파싱·필터·병합·대상유도): **실측 문서 형태의 소형 샘플 JSON**(테스트 픽스처)으로 검증. 네트워크 불필요.
- `data_remote`: Firestore REST 응답 형식 파싱은 순수함수라 픽스처로; 실제 HTTP는 테스트하지 않음(수동 스모크로 대체).
- 캐시 read/write 라운드트립(tmp_path).
- TimetableWidget(qtbot): 캐시 주입 상태에서 그리드 렌더·대상 변경·오늘 강조를 검증. FetchWorker는 스레드 없이 파싱 함수 직접 호출로 대체 검증.
- 수동 스모크: 실 DB 1회 호출(개발 시).

## 9. 에러·엣지

- 시간표 0개/activeTableId 불일치 → 첫 시간표 fallback, 그것도 없으면 "데이터 없음".
- 대상이 데이터에서 사라짐(예: 학급 개편) → 그리드 빈 표시 + 대상 변경 유도 문구.
- duration(연속 차시) 필드는 현 데이터에 없음 — 등장 시 period 단위로만 표시(무시).
- 문서 1.1MB: 시작 시 1회+시간당 1회 다운로드는 허용 범위. 향후 문제 시 updatedAt 비교로 스킵 최적화(범위 밖).

## 10. 범위 밖(후속)

- 현재 교시 강조(교시 시각 설정은 Phase 5 교시 타이머에서 도입 후 연동).
- updatedAt 조건부 갱신 최적화, 다중 시간표 선택 UI(활성 시간표만 표시).
