# Phase 3 — 외부형 위젯 3종 설계 문서 (주간학습계획 · 급식 · 날씨)

- 작성일: 2026-07-02
- 상위 설계: [2026-06-29-teacher-desktop-widgets-design.md](2026-06-29-teacher-desktop-widgets-design.md) §6(위젯 2·3·4)
- 전제: Phase 2에서 확립된 패턴 재사용 — `core/data_remote.py`(익명 인증·REST·캐시), FetchWorker(QThread), show/hide 시 타이머 관리, 오프라인 캐시+상태 라벨, `_custom_menu_actions` 훅.

## 0. 공통 원칙

- 세 위젯 모두 **읽기 전용 외부형**. 캐시는 `teacher-widgets-data/cache/<widget>.json`, config.json에 데이터 저장 금지.
- **fetch 수명주기:** showEvent에서 타이머 시작+즉시 갱신, hideEvent에서 정지 (시간표와 동일). 실패 시 캐시 유지 + "갱신 실패" + 에러 툴팁.
- **429/할당량:** edu-plan 프로젝트가 무료 할당량 소진 시 429(RESOURCE_EXHAUSTED)를 반환함을 실측 확인 — 위젯은 이를 일반 실패로 처리(캐시 표시). 갱신 주기를 보수적으로 잡아 위젯이 할당량을 잠식하지 않게 한다.
- **SSL(실측 발견):** Python 3.13+ 기본 `VERIFY_X509_STRICT`가 나이스 정부 인증서(AKI 확장 누락)를 거부 → `data_remote`에 "체인 검증 유지 + strict 플래그만 해제"한 공용 SSLContext를 도입하고 모든 HTTP 함수가 사용.
- 새 pip 의존성 금지(stdlib urllib).

## 1. data_remote 확장 (공용)

- `_ssl_context()` — `ssl.create_default_context()` 후 `verify_flags &= ~ssl.VERIFY_X509_STRICT`. 모듈 캐시.
- `http_get_json(url, headers=None, timeout=20) -> dict` — 공용 GET(JSON).
- `firestore_run_query(project_id, parent_path, structured_query, id_token, timeout=30) -> list[dict]` — `POST :runQuery`, `document`가 있는 행만 반환.
- 기존 `anon_sign_in`/`firestore_get_document`/`read_cache`/`write_cache`는 그대로(내부적으로 공용 컨텍스트 사용하도록 정리).

## 2. 위젯 ② 주간학습계획 (weekly_plan)

**데이터 소스 (코드 분석 완료, 실측은 할당량 리셋 후 스모크에서):**
- Firebase 프로젝트 `sunil-edu-plan`, 익명 인증. apiKey `AIzaSyA2R8xghbMYtVDvo1D0QbxKnfDSwoSPszU`.
- 일정: `artifacts/sunil-edu-plan/public/data/schedules` 컬렉션. 문서: `{date:"YYYY-MM-DD", department, content, link?, fileName?, order?}`. `department`에 '학사일정'(강조 대상)과 학년·부서명이 섞임.
- 말씀: `.../weekly_messages/{이번주 월요일 YYYY-MM-DD}` 문서: `{principal, vicePrincipal, journal}`.
- 조회: `runQuery`로 **이번 주 월요일 ~ 다음 주 월요일** date 범위만 (수십 건, 경량).

**표시 — 내용 구간(breakpoint) 최초 실전 적용 (`resolve_breakpoint`):**
- 높이 기준 3단: `compact`(오늘만) / `two_days`(오늘+내일) / `week`(월~금+다음주 월, 여유 시 교장·교감 말씀 1줄씩).
  - 임계값: height `(0,"compact")`, `(300,"two_days")`, `(480,"week")`.
- 날짜 카드: 요일·날짜 헤더(오늘 강조), 항목 = `[학사일정]` 주황 배지 또는 `[부서명]` 회색 배지 + content. 항목 정렬: 학사일정 먼저, 이후 order.
- 오늘이 주말이면 다음 주 월요일 기준으로 표시.
- 상단 헤더 "주간학습계획" + 갱신 상태.
- **더블클릭 → 웹앱 앱모드** (시간표의 `build_app_command`/`open_webapp` 패턴 재사용). URL 기본값 `https://sunil-edu-plan.vercel.app/` (config에서 변경 가능 — 실제 배포 URL 확인 필요 시 스모크에서 검증).

**config 기본값 (`weekly_plan`):** api_key, project_id="sunil-edu-plan", artifact_app_id="sunil-edu-plan", webapp_url, refresh_minutes=30.

## 3. 위젯 ⑤ 급식 (meal)

**데이터 소스 (실측 검증 완료 — 키 없이 성공):**
- 나이스 교육정보 개방 포털 `mealServiceDietInfo`: `https://open.neis.go.kr/hub/mealServiceDietInfo?Type=json&ATPT_OFCDC_SC_CODE={edu}&SD_SCHUL_CODE={school}&MLSV_FROM_YMD={from}&MLSV_TO_YMD={to}`.
- **학교: 서울 은평구 선일초등학교 — edu `B10`, school `7031170`** (실측 검증: 실제 당일 메뉴+칼로리 수신).
- 인증키 없이 동작(트래픽 제한 존재 가능) — config에 `api_key` 선택 필드(비어있으면 미첨부, 채우면 `&KEY=` 첨부). 위젯은 하루 몇 회 수준이라 키 없이 충분.
- 응답 필드: `DDISH_NM`(메뉴, `<br/>` 구분, `(알레르기코드)` 괄호), `CAL_INFO`, `MLSV_YMD`, `MMEAL_SC_NM`(조식/중식/석식).

**표시 — 내용 구간 2단:**
- `today`(기본): 오늘 중식 메뉴 리스트 + 칼로리. 알레르기 코드는 작은 회색 첨자로.
- `week`(height ≥ 420): 이번 주 월~금 급식(요일별 접힌 한 줄 또는 오늘 확대+나머지 축약).
- 주말/방학 등 데이터 없음 → "오늘은 급식 정보가 없습니다".
- 조회 범위: 이번 주 월~금 5일치 한 번에 (요청 1회), 캐시.

**config 기본값 (`meal`):** edu_code="B10", school_code="7031170", api_key="", refresh_minutes=360(6시간).

## 4. 위젯 ⑦ 날씨 (weather)

**데이터 소스 (실측 검증 완료 — 키 불필요):**
- Open-Meteo forecast: `current=temperature_2m,weather_code` + `daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max`, `timezone=Asia/Seoul`, `forecast_days=2`.
- Open-Meteo air-quality: `current=pm10,pm2_5`.
- 좌표 기본: **서울 은평구 선일초 인근 lat 37.617, lon 126.921** (config 변경 가능). 원설계의 기상청/에어코리아 대신 Open-Meteo로 확정(키·가입 불필요; 미세먼지는 모델 기반치임을 인지).
- weather_code(WMO) → 한글 상태·이모지 매핑 테이블(맑음☀️/구름☁️/비🌧️/눈🌨️ 등 대표 10여 개).
- PM10/PM2.5 → 한국 환경부 4단계 등급(좋음/보통/나쁨/매우나쁨) 변환: PM10 (0-30/31-80/81-150/151+), PM2.5 (0-15/16-35/36-75/76+).

**표시:**
- 기본: 현재기온(크게)+상태 이모지, 오늘 최고/최저, 미세먼지 등급 배지(PM10·PM2.5).
- 여유(height ≥ 300): 내일 최고/최저+강수확률 줄 추가.
- 요청 2회(날씨+공기질)를 한 fetch 사이클에 수행.

**config 기본값 (`weather`):** lat=37.617, lon=126.921, refresh_minutes=30.

## 5. 컴포넌트 구조

```
core/data_remote.py      # (확장) _ssl_context, http_get_json, firestore_run_query
widgets/weekly_plan.py   # 순수(질의 생성·파싱·일자 그룹·구간 선택) + WeeklyPlanWidget
widgets/meal.py          # 순수(URL 생성·메뉴 파싱·알레르기 분리) + MealWidget
widgets/weather.py       # 순수(URL 생성·파싱·WMO 매핑·등급 변환) + WeatherWidget
main.py                  # weekly_plan, meal, weather 등록
```
- 각 위젯: 시간표의 FetchWorker 패턴(스레드→시그널), showEvent/hideEvent 타이머, aboutToQuit bounded wait, 캐시 주입형 테스트(`_skip_initial_fetch` 가드) 동일 적용.

## 6. 테스트 전략

- 순수 함수(질의 JSON 생성, 응답 파싱, 날짜 그룹핑, breakpoint 선택, WMO/등급 매핑, 알레르기 분리)는 실측 응답 형태의 픽스처로. 네트워크 금지.
- 위젯은 캐시 주입 렌더 검증(qtbot). 실 API 스모크는 마지막 작업에서 1회(주간계획은 할당량 리셋 후).

## 7. 엣지·에러

- 주간계획: 주말→다음 주 기준, 항목 0건 날짜는 "일정 없음", weekly_messages 404는 빈 말씀(정상), runQuery 인덱스 오류(400) 시 실패 처리+툴팁.
- 급식: 나이스 "해당하는 데이터가 없습니다"(INFO-200)는 빈 식단으로 정상 처리. `<br/>` 및 괄호 알레르기 파싱 견고성.
- 날씨: 필드 누락 시 "-" 표시. 두 요청 중 하나만 실패해도 성공분은 반영.

## 8. 범위 밖(후속)

- edu-plan 웹앱의 백업 읽기 폭증 최적화(별도 저장소 작업), 기상청/에어코리아 실측치 전환 옵션, 급식 석식/조식 표시.
