# 에이전트 API 명세 (v2)

Base URL: API 서버 루트 (예: `http://127.0.0.1:5050`). Prefix: `/agent`.

## GET /agent/health

API 연결 상태 확인. (프록시 사용 시 대시보드에서 연결 여부 표시용)

### 응답 (200)

- `status`: "ok", `service`: "nanoquant-api"

---

## POST /agent/chat

사용자 메시지를 받아 ReAct 에이전트를 실행하고 최종 응답을 반환한다.

### 요청 (JSON body)

| 항목 | 타입 | 필수 | 설명 |
|------|------|------|------|
| content | string | O | 사용자 메시지 |
| session_id | string | X | 세션 ID. 없으면 새로 발급 |
| api_key | string | X | LLM API 키 (없으면 서버 .env 사용) |
| model | string | X | "claude" \| "gpt" |

### 응답 (200)

- `content`: 에이전트 최종 응답 텍스트
- `session_id`: 세션 ID
- `tool_calls`: 이번 호출에서 사용된 스킬 목록. 각 항목: `skill`, `args`, `result_preview` 또는 `error`, HITL 시 `hitl_required`, `hitl_id`

### 에러

- 400: content 누락
- 500: 서버/LLM/스킬 오류

---

## POST /agent/approve

HITL 대기 항목에 대한 승인/거절.

### 요청 (JSON body)

| 항목 | 타입 | 필수 | 설명 |
|------|------|------|------|
| hitl_id | string | O | 채팅 응답에서 받은 hitl_id |
| session_id | string | X | 일치 검사용 |
| approved | boolean | O | true=실행, false=취소 |

### 응답 (200)

- 승인 후 성공: `content`, `approved: true`, `skill`, `result_preview`
- 거절: `content: "취소되었습니다."`, `approved: false`
- 404: hitl_id 없음/만료

---

## GET /agent/skills

가용 스킬 목록 및 HITL 대상 스킬 목록.

### 응답 (200)

- `skills`: `{ name, description, params_schema }[]`
- `hitl_skills`: string[]

---

## GET /agent/kg/recent

지식그래프 최근 스킬 사용 이력.

### Query

- `limit`: number (기본 20, 1~100)

### 응답 (200)

- `decisions`: `{ id, session_id, skill_name, args, result_summary, timestamp }[]`

---

## GET /agent/sessions

세션 목록 조회 (최신순).

### 응답 (200)

- `sessions`: `{ id, title, updated_at }[]`

---

## POST /agent/sessions

새 채팅 세션 생성.

### 요청 (JSON body)

| 항목 | 타입 | 필수 | 설명 |
|------|------|------|------|
| title | string | X | 세션 제목 (최대 120자). 생략 시 "새 대화" 등으로 표시 |

### 응답 (201)

- `session_id`: string

---

## GET /agent/sessions/:id

특정 세션 메타 및 대화 히스토리 조회.

### 응답 (200)

- `session_id`, `title`, `updated_at`, `history`: Turn[]

### 에러

- 404: 세션 없음

---

## DELETE /agent/sessions/:id

세션 삭제.

### 응답 (200)

- `ok`: true

### 에러

- 404: 세션 없음
