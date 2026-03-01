# 지식그래프 — 에이전트 참고·영속성

## 에이전트가 KG를 "참고"하는 방식 (선택)

ReAct가 **추론 전**에 KG를 읽어 프롬프트에 넣으면 "과거 유사 사례"를 참고할 수 있다.

| 방식 | 설명 |
|------|------|
| **최근 N건 주입** | 매 턴(또는 첫 턴)에 `getRecentDecisions(5)` 결과를 프롬프트에 "Recent agent decisions:" 형태로 추가. |
| **티커/스킬별 조회** | 사용자 메시지에서 티커·스킬이 파싱되면 `getDecisionsByTicker(ticker)` 또는 `getDecisionsBySkill(skillName)` (API·kg 함수 확장 필요) 결과만 주입. |
| **스킬 메타+통계** | "이 스킬은 지금까지 N번 호출됐고, 최근 결과는 …" 형태로 KG 통계를 프롬프트에 붙임. |

구현: ReAct `buildPrompt` 안에서 `kg.getRecentDecisions(n)` 또는 새 함수 호출 → 문자열로 포맷 → prompt에 추가. (API가 아니라 서버 내부에서만 KG 읽기)

## 영속성 (Persistence)

| 현재 | 1단계 권장 | 2단계 |
|------|------------|--------|
| in-memory (Map, edges 배열) | 서버 재시작 시 KG 소실 | **SQLite** (또는 기존 퀀트 DB)에 nodes·edges 테이블로 저장. API 서버 기동 시 로드. | 동일 + 백업·마이그레이션, 또는 Neo4j 등 전용 그래프 DB 검토. |

영속화 시 `addSkillUse`, `addNode`, `addEdge` 호출 시점에 DB insert. `getRecentDecisions`, `getGraph` 등은 DB 쿼리로 대체.  
→ KG가 "서비스를 쓰면 쓸수록 쌓이고, 재시작해도 유지"되면 "성장형" 에이전트의 기반이 된다.
