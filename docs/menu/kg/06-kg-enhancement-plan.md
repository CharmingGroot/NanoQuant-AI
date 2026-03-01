# 지식그래프 — 구체화·고도화 기획

현재 in-memory 기반의 KG를 **데이터 모델·쓰기/읽기·API·뷰어·에이전트 참고·영속성**까지 단계적으로 구체화·고도화하기 위한 기획. KG는 "에이전트 성장"의 필수 기반이므로, 스텁에서 실제로 쌓이고 활용되는 구조로 전환하는 로드맵을 담는다.

---

## 1. 현황 정리

| 구분 | 현재 상태 | 부족한 점 |
|------|-----------|-----------|
| **데이터** | 노드 타입: indicator, skill, decision. 엣지: used_in. in-memory(Map, 배열) | 영속성 없음(재시작 시 소실). Indicator 노드 미사용. Rule·Strategy 등 확장 타입 없음. |
| **쓰기** | addSkillUse(채팅 스킬 실행 직후, HITL 승인 후) | 스킬 등록 시 Skill 노드 동기화, 백테스트 결과 기록, HITL 상세 메타 없음. |
| **읽기** | getRecentDecisions(limit), getGraph() | getDecisionById, getDecisionsByTicker, getDecisionsBySkill, 타입별/기간별 필터 없음. |
| **API** | GET /agent/kg/recent, GET /agent/kg/graph | /agent/kg/nodes, /agent/kg/decisions/:id, /agent/kg/skills, 쿼리 파라미터(타입·기간·세션·티커) 미지원. |
| **뷰어 UI** | 노드·엣지 수, Decision 테이블, Skill 테이블, 클릭 시 상세 패널, "세션 보기" 링크 | **실제 그래프 시각화**(노드-엣지 배치·드래그) 없음. 타입/기간/세션 필터, 검색, 페이지네이션 미구현. |
| **에이전트 참고** | 없음 | ReAct 프롬프트에 "최근 결정"·티커/스킬별 결정 주입 미구현. |
| **영속성** | 없음 | SQLite(또는 DB) 저장·복구 미구현. |

---

## 2. 데이터 모델 구체화

### 2.1 노드 타입·스키마

| 타입 | id 형식 | data 필드 | 용도 |
|------|---------|-----------|------|
| **skill** | `skill:{name}` | name, description(선택) | 스킬 메타. 스킬 사용 시 ensureSkill로 생성. |
| **decision** | `decision:{timestamp}_{random}` | session_id, skill_name, args, result_summary, error?, timestamp | 에이전트가 스킬을 실행한 "판단" 한 건. |
| **indicator** | `indicator:{name}` | name, description(선택) | (추후) RSI, MA 등 지표 메타. Decision이 "어떤 지표를 참고했는지" 연결용. |
| **rule** | `rule:{id}` | name, description, params_schema(선택) | (추후) "RSI 30 이하 매수" 같은 규칙. 백테스트·전략과 연결. |
| **backtest_result** | `backtest:{run_id}` | run_id, start_date, end_date, symbols[], strategy, total_return_pct, max_drawdown_pct, ... | (추후) 백테스트 1회 실행 결과. Rule·Strategy와 연결. |

1단계에서는 **skill**, **decision** 만 명확히 정의. indicator·rule·backtest_result 는 2단계 이후 확장.

### 2.2 엣지 타입

| 타입 | from → to | 의미 |
|------|------------|------|
| **used_in** | decision → skill | 이 결정에서 해당 스킬을 사용함. (현재 구현됨) |
| **references** | decision → indicator | (추후) 이 결정이 참고한 지표. |
| **uses_rule** | decision → rule | (추후) 이 결정이 적용한 규칙. |
| **validates** | backtest_result → rule | (추후) 이 백테스트가 해당 규칙을 검증함. |

1단계: **used_in** 만 유지.

### 2.3 Decision 데이터 상세

- **필수**: id, session_id, skill_name, args, result_summary, timestamp.
- **선택 확장**: error(에러 메시지), tickers( args에서 추출한 티커 배열, 조회 가속용), duration_ms(실행 시간).

args에서 `ticker`/`symbol` 등을 파싱해 **tickers** 배열을 저장하면, "이 티커로 과거에 뭘 했는지" 쿼리 시 인덱스로 활용 가능.

---

## 3. 쓰기(Write) 구체화·확장

### 3.1 현재 유지

| 시점 | 동작 |
|------|------|
| POST /agent/chat 성공 후 (HITL 없는 tool_call) | addSkillUse(sessionId, skill, args, result_preview, error) |
| POST /agent/approve, approved=true 후 | addSkillUse(sessionId, skill, args, result_summary) |

### 3.2 확장 제안

| 시점 | 동작 | 비고 |
|------|------|------|
| **스킬 레지스트리 로드/등록 시** | ensureSkill(name, description) 호출. (이미 구현) 앱 기동 시 등록된 모든 스킬에 대해 한 번씩 ensureSkill 호출해 Skill 노드 동기화. | 뷰어에서 "사용된 스킬"뿐 아니라 "등록된 전체 스킬" 표시 가능. |
| **백테스트 완료 시** | (추후) backtest_result 노드 추가 + strategy/rule 노드와 엣지. | 4단계. |
| **HITL 승인 시 메타** | addSkillUse 시 approved_at, approval_result 등 필드 추가(선택). | 감사·이력 분석용. |

---

## 4. 읽기(Read)·API 구체화

### 4.1 kg 모듈 함수 확장

| 함수 | 용도 | 비고 |
|------|------|------|
| getRecentDecisions(limit) | (기존) 최근 N건 | 유지. |
| getGraph() | (기존) 뷰어용 노드·엣지 일괄 | 유지. |
| **getDecisionById(id)** | 뷰어에서 노드 클릭 시 상세 | 신규. |
| **getDecisionsByTicker(ticker, limit?)** | 에이전트 참고: "이 티커로 과거에 뭘 했는지" | 신규. args 또는 tickers 필드에서 검색. |
| **getDecisionsBySkill(skillName, limit?)** | 에이전트 참고: "이 스킬 최근 사용 이력" | 신규. |
| **getDecisionsBySession(sessionId)** | 뷰어: 특정 세션의 결정만 필터 | 신규. |
| **getSkills()** | Skill 노드 목록 (뷰어·통계) | ensureSkill 기준으로 노드 조회. |
| **getNodes(type?, fromTs?, toTs?)** | 타입·기간 필터 노드 목록 | 뷰어 필터·페이지네이션용. |

### 4.2 API 엔드포인트 확장

| 메서드 | 경로 | 용도 | 응답 |
|--------|------|------|------|
| GET | /agent/kg/recent?limit= | (기존) 최근 Decision | `{ decisions: [...] }` |
| GET | /agent/kg/graph | (기존) 노드·엣지 일괄 | `{ nodes, edges }` |
| GET | **/agent/kg/decisions/:id** | 단일 Decision 상세 (뷰어 클릭) | `{ id, session_id, skill_name, args, result_summary, timestamp, ... }` |
| GET | **/agent/kg/skills** | Skill 노드 목록 | `{ skills: [{ id, name, description }] }` |
| GET | **/agent/kg/nodes?type=&from=&to=&limit=** | 타입·기간 필터 노드 | `{ nodes: [...] }` |
| GET | (선택) /agent/kg/decisions?ticker=&skill=&session_id=&limit= | 쿼리 파라미터로 Decision 검색 | `{ decisions: [...] }` |

뷰어에서 "해당 세션 보기"로 넘어갈 때는 기존처럼 session_id를 클라이언트에서 가지고 채팅 탭으로 이동하면 됨. /agent/kg/decisions/:id 는 상세 패널용.

---

## 5. 뷰어 UI 구체화·고도화

### 5.1 현재

- 탭: "지식그래프". GET /agent/kg/graph 로 노드·엣지 로드.
- 표시: 노드·엣지 개수, Decision 테이블(스킬, 세션, 결과 요약, 시각, "세션 보기", 상세 버튼), Skill 테이블.
- 클릭: 노드 선택 시 상세 패널에 id, type, data(JSON) 표시.

### 5.2 구체화

| 항목 | 내용 |
|------|------|
| **레이아웃** | 상단: 제목 + "새로고침". 중앙: (1) **그래프 시각화 영역** 또는 (2) **테이블 뷰** 전환 가능. 하단 또는 측면: 선택 노드 상세 패널. |
| **그래프 시각화** | 노드를 원/카드로, 엣지를 선으로 배치. 라이브러리: D3, vis-network, Cytoscape.js, React Flow(또는 Lit 용 경량 그래프) 등. Decision–Skill 관계만 그려도 1단계 충분. 노드 클릭 시 상세 패널 갱신, "세션 보기" 링크 제공. |
| **테이블 뷰** | 기존 Decision·Skill 테이블 유지. 정렬(시각, 스킬명), 페이지네이션(limit/offset) 또는 "더 보기". |
| **필터** | 타입(Decision만 / Skill만 / 전체), 기간(시작일~종료일), 세션 ID(드롭다운 또는 입력). 필터 적용 시 GET /agent/kg/nodes?type=&from=&to= 또는 /agent/kg/recent?limit= 등 호출. |
| **검색** | (고도화) 스킬명·티커·세션 ID 검색어 입력 → decisions 쿼리 API 호출. |
| **빈/에러 상태** | 노드 0개: "아직 기록된 결정이 없습니다. 채팅에서 에이전트를 사용하면 여기에 쌓입니다." API 실패: "불러오기 실패. 새로고침해 주세요." |

### 5.3 반응형

- 좁은 화면: 그래프 영역 접기 또는 테이블만 표시. 상세 패널은 하단 전체 너비 또는 모달.

---

## 6. 에이전트 참고(ReAct 주입) 구체화

### 6.1 목적

ReAct가 응답할 때 "과거에 이 티커로 RSI 조회했고 결과가 OO였다" 같은 맥락을 프롬프트에 넣으면, 일관성·재사용 인식에 도움이 됨.

### 6.2 주입 방식

| 방식 | 시점 | 내용 | 구현 |
|------|------|------|------|
| **최근 N건** | 매 턴(또는 첫 턴만) | getRecentDecisions(5) → "Recent agent decisions: ..." 문자열로 buildPrompt에 추가. | react.ts에서 kg.getRecentDecisions(5) 호출 후 포맷해 prompt lines에 push. |
| **티커별** | 사용자 메시지에 티커 심볼이 있을 때 | getDecisionsByTicker(ticker, 5) → "Past decisions for {ticker}: ..." | 메시지에서 티커 추출(간단 정규 또는 스킬 스키마 참고) 후 조건부 호출. |
| **스킬별** | (선택) 사용된 스킬이 적을 때 | getDecisionsBySkill(skillName, 3) | 동일. |

### 6.3 프롬프트 포맷 예시

```
Recent agent decisions (for context):
1. [session-xxx] get_rsi_for_ticker(ticker=AAPL) → RSI 45.2
2. [session-yyy] get_current_price(ticker=SOFI) → 12.34
...
```

에이전트가 "이전에 비슷한 걸 했구나"를 인지하도록 짧게만 넣고, 토큰을 많이 쓰지 않도록 limit는 3~5 권장.

---

## 7. 영속성(Persistence) 구체화

### 7.1 목표

서버 재시작 후에도 KG가 유지되어 "서비스를 쓸수록 쌓이는" 성장형 기반이 되도록 함.

### 7.2 저장소 옵션

| 옵션 | 설명 | 장단점 |
|------|------|--------|
| **SQLite** | nodes·edges 테이블. API 서버와 같은 프로세스에서 파일 DB 접근. | 구현 단순, 의존성 적음. 확장 시 마이그레이션 필요. |
| **기존 퀀트 DB** | 이미 PostgreSQL 등이 있으면 nodes/edges 테이블 추가. | 인프라 통합. nanoquant-ai가 Node만 쓰면 연동 비용 있음. |
| **Neo4j 등 그래프 DB** | (2단계) 전용 그래프 DB. | 관계 쿼리·탐색에 유리. 운영 복잡도 증가. |

1단계 권장: **SQLite**. 파일 하나(nanoquant_kg.db 등)에 저장.

### 7.3 SQLite 스키마 제안

```sql
-- 노드: id(PK), type, data(JSON 텍스트), created_at
CREATE TABLE IF NOT EXISTS kg_nodes (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  data TEXT NOT NULL DEFAULT '{}',
  created_at INTEGER NOT NULL
);

-- 엣지: from_id, to_id, type, created_at
CREATE TABLE IF NOT EXISTS kg_edges (
  from_id TEXT NOT NULL,
  to_id TEXT NOT NULL,
  type TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  PRIMARY KEY (from_id, to_id, type),
  FOREIGN KEY (from_id) REFERENCES kg_nodes(id),
  FOREIGN KEY (to_id) REFERENCES kg_nodes(id)
);

-- Decision의 티커 검색 가속 (선택)
CREATE INDEX IF NOT EXISTS idx_kg_nodes_type ON kg_nodes(type);
CREATE INDEX IF NOT EXISTS idx_kg_nodes_created ON kg_nodes(created_at);
```

- **data**: JSON.stringify(node.data) 저장. 조회 시 JSON.parse.
- addNode / addEdge 시 INSERT. getGraph / getRecentDecisions 시 SELECT. 기동 시 DB 파일 있으면 로드(또는 in-memory와 동기화).

### 7.4 마이그레이션

- 초기: in-memory만 사용하던 코드 경로 유지.
- 1단계: SQLite 어댑터 도입 후, addNode/addEdge/getGraph/getRecentDecisions 등을 DB 호출로 전환. 기동 시 DB에서 메모리로 로드하거나, 매 요청마다 DB 쿼리.
- (선택) 기존 in-memory를 한 번 DB로 덤프하는 스크립트는 필요 시에만.

---

## 8. 단계별 로드맵 (구체화·고도화)

| 단계 | 목표 | 산출물 |
|------|------|--------|
| **1단계** | **읽기·API·뷰어 보강** | getDecisionById, getSkills 구현. API: GET /agent/kg/decisions/:id, GET /agent/kg/skills. 뷰어: 상세 패널에서 decisions/:id 호출(선택), 필터(타입·기간) UI + /agent/kg/nodes 연동. |
| **2단계** | **영속성** | SQLite 스키마 도입. addNode/addEdge/get* 전부 DB 연동. 서버 재시작 후에도 KG 유지. |
| **3단계** | **에이전트 참고** | getDecisionsByTicker, getDecisionsBySkill 구현. ReAct buildPrompt에서 최근 N건(및 티커/스킬 조건부) 주입. |
| **4단계** | **뷰어 고도화** | 그래프 시각화(노드-엣지 배치). 검색·페이지네이션. (선택) indicator/rule 노드 확장, 백테스트 결과 노드·엣지. |

---

## 9. 문서 간 연결

- **개요**: [01-overview.md](01-overview.md)
- **쓰기·읽기·흐름**: [02-write-read-flow.md](02-write-read-flow.md)
- **API**: [03-api.md](03-api.md)
- **뷰어 UI**: [04-viewer-ui.md](04-viewer-ui.md)
- **에이전트 참고·영속성**: [05-agent-reference-and-persistence.md](05-agent-reference-and-persistence.md)
- **원본 상세**: [../../kg-service-integration.md](../../kg-service-integration.md)
- **본 문서**: 구체화·고도화 로드맵 및 데이터/쓰기/읽기/API/뷰어/에이전트/영속성 상세.

구현 시 1단계(API·뷰어 필터·상세)부터 순차 진행하면, 현재 뷰어를 유지하면서도 조회·탐색이 강화되고, 이어서 영속성과 에이전트 참고까지 단계적으로 도입할 수 있다.
