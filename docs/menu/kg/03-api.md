# 지식그래프 — API

## 현재

| 메서드 | 경로 | 용도 | 응답 |
|--------|------|------|------|
| GET | /agent/kg/recent?limit | 최근 Decision 목록 | `{ decisions: [{ id, session_id, skill_name, args, result_summary, timestamp }] }` |

## 확장 (뷰어·연동용)

| 메서드 | 경로 | 용도 | 응답 예시 |
|--------|------|------|-----------|
| GET | /agent/kg/graph | 뷰어용: 노드·엣지 일괄 | `{ nodes: [{ id, type, data }], edges: [{ from_id, to_id, type }] }` |
| GET | /agent/kg/nodes | 노드 목록 (타입별 필터 선택) | `{ nodes: [...] }` |
| GET | /agent/kg/decisions/:id | 단일 Decision 상세 (뷰어 클릭 시) | `{ id, session_id, skill_name, args, result_summary, timestamp }` |
| GET | /agent/kg/skills | Skill 노드 목록 (뷰어·통계) | `{ skills: [{ id, name, description }] }` |

- **/agent/kg/graph**: 뷰어에서 "전체 그래프" 또는 "Decision–Skill 관계만" 그리기.
- **/agent/kg/decisions/:id**: 뷰어에서 노드 클릭 시 해당 채팅 세션(`/agent/sessions/:id`)으로 넘어가기 위한 상세 조회.
