# 지식그래프 — 쓰기·읽기 시점·서비스 흐름

## 데이터가 KG에 들어가는 시점 (쓰기)

| 시점 | 트리거 | 기록 내용 |
|------|--------|-----------|
| **채팅 응답 직후** | POST /agent/chat 성공, ReAct가 스킬 실행 완료 | HITL이 **필요 없는** 각 tool_call에 대해 `addSkillUse(sessionId, skill, args, result_preview, error)`. |
| **HITL 승인 후** | POST /agent/approve, approved=true, 스킬 실행 완료 | 해당 스킬 실행 결과를 `addSkillUse(sessionId, skill, args, result_summary)` 로 기록. |
| **(추후) 스킬 등록 시** | 새 스킬/지표가 레지스트리에 등록 | KG에 **Skill** 또는 **Indicator** 노드 추가. |
| **(추후) 백테스트 완료 시** | 백테스트 API 완료 | 전략·기간·수익률을 KG에 기록. |

현재 구현: **채팅 응답** + **HITL 승인 후** 두 시점만 반영. 둘 다 `kg.addSkillUse` 호출.

## KG 데이터를 쓰는 시점 (읽기)

| 소비처 | 용도 | API/방식 |
|--------|------|----------|
| **대시보드** | "최근 결정" 카드·테이블 | `GET /agent/kg/recent?limit=N` |
| **모니터 탭** | "실시간 활동" 테이블 | 동일 `GET /agent/kg/recent` |
| **지식그래프 뷰어** | 노드·엣지 탐색, 시각화 | `GET /agent/kg/graph` 등 (API 확장) |
| **(추후) ReAct 프롬프트** | "유사 과거 사례" 주입 | getRecentDecisions / getDecisionsByTicker 등 (서버 내부) |

## 서비스 흐름 요약

```
[사용자] 채팅 입력 → POST /agent/chat → ReAct 스킬 실행 → kg.addSkillUse(...)  ← KG 쓰기

[대시보드/모니터] GET /agent/kg/recent → getRecentDecisions(limit)  ← KG 읽기 → 테이블 렌더링

[지식그래프 뷰어] GET /agent/kg/graph → 노드·엣지 시각화, 클릭 시 상세·세션 링크
```
