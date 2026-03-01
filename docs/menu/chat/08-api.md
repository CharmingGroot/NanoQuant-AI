# AI 채팅 — API

## 세션

| 메서드 | 경로 | 용도 |
|--------|------|------|
| GET | /agent/sessions | 목록 조회 (`id`, `title`, `updated_at`) |
| POST | /agent/sessions | 새 세션 생성 (body `title` 선택) |
| GET | /agent/sessions/:id | 단일 세션 메타·히스토리 |
| DELETE | /agent/sessions/:id | 세션 삭제 |
| **PATCH** | **/agent/sessions/:id** | **제목 수정** (body `{ "title": string }`, 최대 120자) — **명세·구현 추가 필요** |

## 채팅·HITL

| 메서드 | 경로 | 용도 |
|--------|------|------|
| POST | /agent/chat | 사용자 메시지 전송, ReAct 실행, 응답·tool_calls 반환. body: `content`, `session_id`, `api_key`, `model` (선택), **`force_skill`** (선택, 스킬명 문자열 — 이번 요청에서 해당 스킬 우선 사용). |
| POST | /agent/approve | HITL 승인/거절. body: `hitl_id`, `session_id` (선택), `approved`. |

참고: [agent-api-spec.md](../../agent-api-spec.md) — 세션·채팅·HITL 상세 명세.
