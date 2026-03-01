# 대시보드 — API

## 포트폴리오

| 항목 | 내용 |
|------|------|
| **데이터 소스** | 기존 시뮬레이션·DB·또는 스킬(예: `get_portfolio`, `get_positions`) 호출 결과. 초기에는 스킬/API로 포트폴리오 조회 엔드포인트 제공. |
| **API 제안** | `GET /agent/portfolio` 또는 `GET /portfolio` |
| **응답 예시** | `{ total_asset, cash, positions: [{ symbol, name?, qty, avg_price, current_price, value, pnl, pnl_pct, weight_pct? }], pnl_today?, updated_at }` |
| **새로고침** | 사용자 새로고침 버튼 클릭 시 해당 API 재호출, 로딩 표시 후 카드·테이블 갱신. |

## 기타 대시보드 데이터

- **연결**: `GET /agent/health`
- **스킬**: `GET /agent/skills`
- **세션 목록**: `GET /agent/sessions` (목록 길이 또는 메타)
- **최근 결정**: `GET /agent/kg/recent?limit=N`
