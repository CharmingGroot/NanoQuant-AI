# 백테스트 — API·우선순위

## 데이터·API

| 항목 | 내용 |
|------|------|
| **과거 데이터** | 백테스트 엔진이 **과거 일봉(또는 분봉)** 가격·지표(RSI 등)를 조회할 수 있어야 함. 기존 퀀트 DB·yfinance·스킬 로직을 "날짜 구간"으로 호출하는 **히스토리 API**가 있으면 재사용. |
| **API 제안** | `POST /agent/backtest` (또는 `POST /backtest`) — body: `{ start_date, end_date, symbols[], strategy: { type: "rsi_threshold", params: { period, buy_below, sell_above } } }`. 응답: `{ total_return_pct, annualized_return_pct, sharpe?, max_drawdown_pct, trade_count, win_rate?, equity_curve?: [], trades: [{ date, symbol, side, price, ... }] }`. |
| **스킬** | `run_backtest` 스킬: 위 API를 내부 호출하고, 결과 요약 문자열을 반환. 에이전트가 채팅에서 "백테스트 해줘" 요청 시 이 스킬을 호출. |

## 우선순위 제안

| 단계 | 내용 |
|------|------|
| **1단계** | 백테스트 **탭** + 기간·종목·단일 프리셋(예: RSI 30/70) 입력 폼 + 실행 API + 결과 요약·거래 테이블. 수익 곡선은 단순 선 그래프. |
| **2단계** | `run_backtest` 스킬 등록 → 채팅에서 "백테스트 해줘" 요청 처리. 결과 요약 응답 + 백테스트 탭에 "최근 실행" 노출. |
| **3단계** | 전략 프리셋 추가·사용자 임계값 입력, 실행 이력 저장·비교, 벤치마크 대비. |
