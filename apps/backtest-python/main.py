"""
백테스트 전용 Python 서비스 — Node에서 HTTP로 호출.
GET /history, POST /backtest (pandas·yfinance 기반).
"""
from __future__ import annotations

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from engine import get_history, run_backtest

app = FastAPI(title="NanoQuant Backtest Service", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"status": "ok", "service": "backtest-python"}


@app.get("/history")
def history(
    symbol: str = Query("AAPL"),
    start: str = Query(..., description="YYYY-MM-DD"),
    end: str = Query(..., description="YYYY-MM-DD"),
    interval: str = Query("1d"),
):
    rows = get_history(symbol, start, end, interval)
    return {"symbol": symbol, "interval": interval, "rows": rows}


class StrategyParams(BaseModel):
    period: int | None = 14
    buy_below: float | None = 30.0
    sell_above: float | None = 70.0


class BacktestRequest(BaseModel):
    start_date: str
    end_date: str
    symbols: list[str]
    strategy: dict | None = None  # { "type": "rsi_threshold", "params": { ... } }


@app.post("/backtest")
def backtest(req: BacktestRequest):
    symbols = req.symbols or ["AAPL"]
    strat = req.strategy or {}
    params = strat.get("params") or {}
    period = int(params.get("period", 14))
    buy_below = float(params.get("buy_below", 30))
    sell_above = float(params.get("sell_above", 70))
    result = run_backtest(
        start_date=req.start_date,
        end_date=req.end_date,
        symbols=symbols,
        period=period,
        buy_below=buy_below,
        sell_above=sell_above,
    )
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5052)
