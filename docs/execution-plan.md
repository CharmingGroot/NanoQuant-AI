# 기획 대비 실행 계획

docs/menu 기획서 및 구체화·고도화 기획에 따른 **실행 우선순위**와 **단계별 작업** 정리.

---

## 1. 우선순위 원칙

- **KG 1단계** 먼저: API·뷰어만 확장하면 되고, 외부 데이터 소스 불필요. 단기 완료 가능.
- **백테스트 1단계** 다음: 히스토리 API + 엔진 구현 필요. 일봉 데이터 소스 연동 후 RSI 전략 실연동.
- **run_backtest 스킬**·**KG 2단계(영속성)**·**에이전트 KG 주입**은 1단계 완료 후 진행.

---

## 2. Phase A — 지식그래프 1단계 (06-kg-enhancement-plan)

| # | 작업 | 산출물 |
|---|------|--------|
| A-1 | kg.ts: getDecisionById(id), getSkills(), getNodes(type?, fromTs?, toTs?, limit?) 구현 | kg.ts 확장 |
| A-2 | routes: GET /agent/kg/decisions/:id, GET /agent/kg/skills, GET /agent/kg/nodes?type=&from=&to=&limit= | routes.ts |
| A-3 | 뷰어(kg-tab): 타입 필터(전체/Decision/Skill), 기간 필터(시작·종료) UI + /kg/nodes 또는 /kg/recent 연동 | kg-tab.ts |

**완료 기준**: Decision 상세 조회 API·스킬 목록 API 동작, 뷰어에서 필터로 목록 제한 가능.

---

## 3. Phase B — 백테스트 1단계 (05-backtest-enhancement-plan)

| # | 작업 | 산출물 |
|---|------|--------|
| B-1 | **히스토리 API** GET /agent/data/history?symbol=&start=&end=&interval=d 구현. (Node에서 yahoo-finance2 또는 유사 패키지로 일봉 조회, 없으면 스텁 데이터 반환) | routes.ts, data/history 모듈 |
| B-2 | **RSI 계산** 유틸: close[] → period → rsi[] | backtest 또는 util |
| B-3 | **백테스트 엔진**: 기간·심볼·rsi_threshold 파라미터로 봉 순회 → 시그널 → 매수/매도 시뮬레이션 → total_return_pct, max_drawdown_pct, trades, equity_curve 반환 | backtest/engine.ts |
| B-4 | POST /agent/backtest: body 파싱 후 엔진 호출, 히스토리 API로 일봉 조회 후 결과 반환 (스텁 제거) | routes.ts |
| B-5 | 백테스트 탭 UI: 기존 폼 유지, 결과 카드·거래 테이블이 API 실제 응답으로 표시 (equity_curve 차트는 2단계에서) | backtest-tab.ts |

**완료 기준**: 기간·종목·RSI 전략 선택 후 실행 시 실제 수치·거래 내역이 나옴.

---

## 4. Phase C — 연동·고도화 (2단계)

| # | 작업 | 비고 |
|---|------|------|
| C-1 | ~~run_backtest 스킬 등록~~ → **완료**: run_backtest 스킬 등록됨. 채팅에서 "백테스트 해줘" 요청 시 에이전트가 호출 가능. | 05-backtest 3단계 |
| C-2 | KG 영속성: SQLite 도입, kg_nodes/kg_edges 저장·로드 | 06-kg 2단계 |
| C-3 | ReAct 프롬프트에 getRecentDecisions(N) 주입 (에이전트 참고) | 06-kg 3단계 |
| C-4 | 백테스트: 수익 곡선 차트, 실행 이력 저장·조회 API | 05-backtest 2·3단계 |

---

## 5. 진행 순서 요약

1. **Phase A** (KG 1단계): A-1 → A-2 → A-3
2. **Phase B** (백테스트 1단계): B-1 → B-2 → B-3 → B-4 → B-5
3. **Phase C**: C-1 ~ C-4는 별도 스프린트에서 진행

현재 세션에서는 **Phase A 전부**와 **Phase B**까지 진행한다.

---

## 6. 완료 체크 (최근 반영)

| Phase | 항목 | 상태 |
|-------|------|------|
| A | 실행 계획서 작성 (docs/execution-plan.md) | 완료 |
| A | kg.ts: getDecisionById, getSkills, getNodes | 완료 |
| A | GET /agent/kg/decisions/:id, /kg/skills, /kg/nodes | 완료 |
| A | 뷰어 필터(타입·기간) UI | 완료 |
| B | GET /agent/data/history (스텁 일봉) | 완료 |
| B | RSI 계산 + 백테스트 엔진(rsi_threshold) | 완료 |
| B | POST /agent/backtest 실연동 | 완료 |
| B | 백테스트 탭 결과·거래 테이블 실제 데이터 | 완료 |
| C-3 | ReAct 프롬프트에 getRecentDecisions(5) 주입 (에이전트 참고) | 완료 |
| C-4 | 백테스트 탭 수익 곡선(equity_curve) SVG 차트 표시 | 완료 |
| C-2 | KG SQLite 영속성 (data/nanoquant.db, initFromDb, write-through) | 완료 |
| 백테스트 | 실행 이력 저장·조회 API (POST 응답 run_id, GET /backtest/runs, /backtest/runs/:id) | 완료 |
| 백테스트 | 탭 "최근 실행" UI (목록 클릭 시 해당 결과 로드) | 완료 |
