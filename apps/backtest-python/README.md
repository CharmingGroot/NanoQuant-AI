# NanoQuant Backtest Service (Python)

백테스트·과거 일봉 조회를 담당하는 Python 전용 서비스. Node API는 채팅·에이전트에 집중하고, CPU/데이터 연산은 이 서버로 위임한다.

## 의존성

- Python 3.10+
- fastapi, uvicorn, pandas, yfinance, pydantic

## 설치 및 실행

```bash
pip install -r requirements.txt
python main.py
# 또는
uvicorn main:app --reload --port 5052
```

기본 포트 **5052**. Node 쪽에서 `BACKTEST_SERVICE_URL=http://127.0.0.1:5052` 로 연결하면 된다.

## API

- `GET /health` — 상태 확인
- `GET /history?symbol=AAPL&start=2024-01-01&end=2024-12-31&interval=1d` — yfinance 일봉
- `POST /backtest` — body: `{ "start_date", "end_date", "symbols", "strategy": { "type": "rsi_threshold", "params": { "period", "buy_below", "sell_above" } } }`

응답 형식은 Node 백테스트 엔진과 동일 (total_return_pct, max_drawdown_pct, trades, equity_curve 등).
