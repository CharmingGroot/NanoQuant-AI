# 모니터 — 실시간 활동·API

## UI

| 항목 | 내용 |
|------|------|
| **테이블** | 스킬, 세션, 상태(완료/오류), 결과 요약, 시각. 상태는 pill 등으로 시각 구분. |
| **새로고침** | 섹션별 "새로고침" 버튼으로 `GET /agent/kg/recent` 재호출. (선택) 자동 새로고침·웹소켓. |
| **Last Update** | 데이터 기준 시각 표시(M-6). |

## API

- **GET /agent/kg/recent?limit=20** — 최근 Decision 목록. 응답: `{ decisions: [{ id, session_id, skill_name, args, result_summary, timestamp }] }`.
