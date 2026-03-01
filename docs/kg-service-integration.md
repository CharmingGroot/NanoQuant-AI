# 지식그래프 서비스 연동

지식그래프(KG)를 NanoQuant AI v2 서비스(API·에이전트·UI)와 **어떻게 엮을지** 정리한 문서다. KG는 “에이전트가 무엇을 했는지·무엇을 아는지”를 그래프로 쌓고, 그걸 다시 **모니터링·뷰어·(선택) 에이전트 추론**에 쓰는 구조다.

---

## 1. KG가 서비스에서 하는 역할

| 역할 | 설명 |
|------|------|
| **판단 이력 저장** | 에이전트가 스킬을 실행할 때마다 “누가(세션), 무엇을(스킬+인자), 어떤 결과”를 **Decision** 노드로 기록. |
| **스킬·지표 메타** | 사용된 스킬을 **Skill** 노드로 등록하고, Decision → Skill **used_in** 엣지로 연결. (추후 Indicator, Rule 노드 확장) |
| **모니터링 소스** | 대시보드·모니터 탭의 “최근 결정”은 KG의 Decision 목록을 조회해 표시. |
| **성장 기반** | 나중에 “이 티커로 과거에 뭘 했는지”, “이 스킬이 얼마나 쓰였는지”를 조회해 에이전트 추론·UI 분석에 활용. |

---

## 2. 데이터가 KG에 들어가는 시점 (쓰기)

| 시점 | 트리거 | 기록 내용 |
|------|--------|-----------|
| **채팅 응답 직후** | POST /agent/chat 성공, ReAct가 스킬 실행 완료 | HITL이 **필요 없는** 각 tool_call에 대해 `addSkillUse(sessionId, skill, args, result_preview, error)`. |
| **HITL 승인 후** | POST /agent/approve, approved=true, 스킬 실행 완료 | 해당 스킬 실행 결과를 `addSkillUse(sessionId, skill, args, result_summary)` 로 기록. |
| **(추후) 스킬 등록 시** | 새 스킬/지표가 레지스트리에 등록 | KG에 **Skill** 또는 **Indicator** 노드 추가(ensureSkill 수준 확장). |
| **(추후) 백테스트 완료 시** | 백테스트 API 완료 | 전략·기간·수익률을 KG에 기록해 “이 전략으로 이렇게 나왔음” 참고용으로 활용. |

현재 구현: **채팅 응답** + **HITL 승인 후** 두 시점만 반영됨. 둘 다 `kg.addSkillUse` 호출.

---

## 3. KG 데이터를 쓰는 시점 (읽기)

| 소비처 | 용도 | API/방식 |
|--------|------|----------|
| **대시보드** | “최근 결정” 카드·테이블 | `GET /agent/kg/recent?limit=N` → Decision 목록(세션, 스킬, 결과 요약, 시각) |
| **모니터 탭** | “실시간 활동” 테이블 | 동일 `GET /agent/kg/recent` |
| **지식그래프 뷰어 (UI)** | 노드·엣지 탐색, 시각화 | 아래 §5 API 확장 후 `GET /agent/kg/graph` 등으로 노드/엣지 목록 조회 |
| **(추후) ReAct 프롬프트** | “유사 과거 사례” 주입 | 예: 사용자 질문에 티커가 있으면 `getDecisionsByTicker(ticker)` 또는 `getRecentDecisions(limit)` 결과를 프롬프트에 붙여 “과거에 이렇게 판단했음” 참고 |

---

## 4. 서비스 흐름 요약

```
[사용자] 채팅 입력
    → [API] POST /agent/chat
        → [ReAct] 스킬 결정·실행 (또는 HITL 대기)
        → [API] 스킬 실행 결과마다 kg.addSkillUse(...)  ← KG 쓰기
    → [API] 응답 반환 (content, tool_calls)

[대시보드/모니터 UI] 마운트·새로고침
    → [API] GET /agent/kg/recent?limit=20
    → [KG] getRecentDecisions(limit)  ← KG 읽기
    → [UI] 테이블 렌더링

[지식그래프 뷰어 UI] 탭 진입
    → [API] GET /agent/kg/graph (또는 /nodes, /edges)  ← API 확장
    → [UI] 노드·엣지 시각화, 클릭 시 상세(세션·결정) 링크
```

---

## 5. API 확장 (뷰어·연동용)

현재: `GET /agent/kg/recent?limit` 만 존재. 뷰어와 “에이전트가 KG를 참고”하려면 아래가 필요하다.

| 메서드 | 경로 | 용도 | 응답 예시 |
|--------|------|------|-----------|
| GET | /agent/kg/recent | (기존) 최근 Decision 목록 | `{ decisions: [{ id, session_id, skill_name, args, result_summary, timestamp }] }` |
| GET | /agent/kg/graph | 뷰어용: 노드·엣지 일괄 | `{ nodes: [{ id, type, data }], edges: [{ from_id, to_id, type }] }` |
| GET | /agent/kg/nodes | 노드 목록 (타입별 필터 선택) | `{ nodes: [...] }` |
| GET | /agent/kg/decisions/:id | 단일 Decision 상세 (뷰어에서 클릭 시) | `{ id, session_id, skill_name, args, result_summary, timestamp }` |
| GET | /agent/kg/skills | Skill 노드 목록 (뷰어·통계) | `{ skills: [{ id, name, description }] }` |

- **/agent/kg/graph** 가 있으면 뷰어는 “전체 그래프” 또는 “Decision–Skill 관계만” 그릴 수 있다.
- **/agent/kg/decisions/:id** 는 뷰어에서 노드 클릭 시 해당 채팅 세션(`/agent/sessions/:id`)으로 넘어가기 위한 상세 조회용.

---

## 6. UI 연동 (지식그래프 뷰어)

| 요소 | 동작 |
|------|------|
| **탭 위치** | 네비에 “지식그래프” 탭. (대시보드 | 채팅 | 백테스트 | 모니터 | **지식그래프** | 설정) |
| **데이터 소스** | `GET /agent/kg/graph` (또는 /nodes + /edges) 로 노드·엣지 로드. |
| **표시** | 노드: Skill(스킬명), Decision(요약·시각). 엣지: used_in. (추후 Indicator, Rule 추가 시 타입별 스타일) |
| **인터랙션** | 노드 클릭 → 상세 패널에 id, type, data 표시. Decision 클릭 시 “해당 세션 보기” 링크 → 채팅 탭으로 이동하며 해당 session_id 선택. |
| **필터** | (선택) 타입별 필터(Skill만, Decision만), 기간 필터, 세션별 필터. |

뷰어는 “무엇이 기록돼 있는지” 탐색·검증용. 실시간 모니터링은 기존 대시보드·모니터 탭이 담당.

---

## 7. 에이전트가 KG를 “참고”하는 방식 (선택)

ReAct가 **추론 전**에 KG를 읽어 프롬프트에 넣으면 “과거 유사 사례”를 참고할 수 있다.

| 방식 | 설명 |
|------|------|
| **최근 N건 주입** | 매 턴(또는 첫 턴)에 `getRecentDecisions(5)` 결과를 프롬프트에 "Recent agent decisions:" 형태로 추가. LLM이 “비슷한 일 했던 적 있음”을 인지. |
| **티커/스킬별 조회** | 사용자 메시지에서 티커·스킬이 파싱되면 `getDecisionsByTicker(ticker)` 또는 `getDecisionsBySkill(skillName)` (API·kg 함수 확장 필요) 결과만 주입해 노이즈 감소. |
| **스킬 메타만** | 현재처럼 “Available skills” 메타만 주는 것이 아니라, “이 스킬은 지금까지 N번 호출됐고, 최근 결과는 …” 형태로 KG 통계를 붙일 수 있음. |

구현 시: ReAct `buildPrompt` 안에서 `kg.getRecentDecisions(n)` 또는 새 함수 호출 → 문자열로 포맷 → prompt에 추가. API가 아니라 서버 내부에서만 KG 읽기.

---

## 8. 영속성 (Persistence)

| 현재 | 1단계 권장 | 2단계 |
|------|------------|--------|
| in-memory (kg.ts의 Map, edges 배열) | 서버 재시작 시 KG 소실 | **SQLite** (또는 기존 퀀트 DB)에 nodes·edges 테이블로 저장. API 서버 기동 시 로드. | 동일 + 백업·마이그레이션, 또는 Neo4j 등 전용 그래프 DB 검토. |

영속화 시 `addSkillUse`, `addNode`, `addEdge` 호출 시점에 DB insert (또는 트랜잭션 배치) 추가. `getRecentDecisions`, `getGraph` 등은 DB 쿼리로 대체.  
→ KG가 “서비스를 쓰면 쓸수록 쌓이고, 재시작해도 유지”되면 “성장형” 에이전트의 기반이 된다.

---

## 9. 정리

- **쓰기**: 채팅 스킬 실행 직후 + HITL 승인 후 → `addSkillUse`. (추후 스킬/지표 등록·백테스트 결과)
- **읽기**: 대시보드·모니터는 `/agent/kg/recent`. 뷰어·에이전트 참고를 위해 `/agent/kg/graph`, `/agent/kg/nodes`, `/agent/kg/decisions/:id`, `/agent/kg/skills` 등 확장.
- **UI**: 지식그래프 탭에서 노드·엣지 시각화, Decision 클릭 시 세션으로 드릴다운.
- **에이전트 참고**: (선택) ReAct 프롬프트에 최근 결정·티커/스킬별 결정 주입.
- **성장**: KG를 DB에 저장해 재시작 후에도 유지하면, 장기적으로 “무엇을 얼마나 했는지”가 쌓여 서비스와 에이전트 모두에 활용 가능.

이렇게 엮으면 지식그래프가 “로그”를 넘어 **서비스의 한 축**으로 자리 잡고, 뷰어(필수)와 모니터링·(선택) 추론 개선까지 한 번에 맞춰갈 수 있다.
