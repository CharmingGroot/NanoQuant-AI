"""
백테스트 엔진 — pandas, yfinance 기반.
히스토리 조회 + RSI 임계값 전략 시뮬레이션.
"""
from __future__ import annotations

import pandas as pd

try:
    import yfinance as yf
except ImportError:
    yf = None


def get_history(symbol: str, start: str, end: str, interval: str = "1d") -> list[dict]:
    """yfinance로 일봉 조회. 실패 시 빈 리스트."""
    if not yf:
        return []
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start, end=end, interval=interval or "1d")
        if df.empty:
            return []
        df = df.reset_index()
        df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
        return df[["Date", "Open", "High", "Low", "Close", "Volume"]].rename(
            columns={"Date": "date", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
        ).to_dict(orient="records")
    except Exception:
        return []


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """close 시리즈로 RSI(period) 계산."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    return rsi


def run_backtest(
    start_date: str,
    end_date: str,
    symbols: list[str],
    strategy_type: str = "rsi_threshold",
    period: int = 14,
    buy_below: float = 30.0,
    sell_above: float = 70.0,
    initial_capital: float = 1_000_000.0,
) -> dict:
    """RSI 임계값 전략 백테스트. Node 엔진과 동일한 응답 형식."""
    symbol = symbols[0] if symbols else "AAPL"
    rows = get_history(symbol, start_date, end_date)
    if not rows:
        return {
            "total_return_pct": 0.0,
            "annualized_return_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "trade_count": 0,
            "win_rate": 0.0,
            "equity_curve": [],
            "trades": [],
            "start_date": start_date,
            "end_date": end_date,
        }

    df = pd.DataFrame(rows)
    df["close"] = pd.to_numeric(df["close"], errors="coerce").ffill()
    df = df.dropna(subset=["close"])
    if df.empty or len(df) < period + 1:
        return {
            "total_return_pct": 0.0,
            "annualized_return_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "trade_count": 0,
            "win_rate": 0.0,
            "equity_curve": [1.0] * len(df),
            "trades": [],
            "start_date": start_date,
            "end_date": end_date,
        }

    df["rsi"] = compute_rsi(df["close"], period)
    df = df.dropna(subset=["rsi"])

    trades: list[dict] = []
    position = 0
    entry_price = 0.0
    cash = initial_capital
    equity_curve: list[float] = []

    for _, row in df.iterrows():
        date = row["date"]
        price = float(row["close"])
        rsi = float(row["rsi"])

        if position == 0 and rsi < buy_below:
            qty = int(cash / price)
            if qty > 0:
                position = qty
                entry_price = price
                cash -= price * qty
                trades.append({"date": date, "symbol": symbol, "side": "buy", "price": price, "quantity": qty})
        elif position > 0 and rsi > sell_above:
            pnl = (price - entry_price) * position
            pnl_pct = (price / entry_price - 1) * 100
            cash += price * position
            trades.append({
                "date": date,
                "symbol": symbol,
                "side": "sell",
                "price": price,
                "quantity": position,
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
            })
            position = 0

        equity = cash + position * price
        equity_curve.append(round(equity / initial_capital, 6))

    final_equity = cash + position * float(df.iloc[-1]["close"])
    total_return_pct = (final_equity / initial_capital - 1) * 100
    years = max(0.001, len(df) / 365.0)
    annualized_return_pct = (pow(final_equity / initial_capital, 1 / years) - 1) * 100

    peak = 1.0
    max_drawdown_pct = 0.0
    for e in equity_curve:
        if e > peak:
            peak = e
        dd = (1 - e / peak) * 100
        if dd > max_drawdown_pct:
            max_drawdown_pct = dd

    sell_trades = [t for t in trades if t["side"] == "sell" and "pnl" in t]
    wins = sum(1 for t in sell_trades if t["pnl"] > 0)
    win_rate = (wins / len(sell_trades)) if sell_trades else 0.0

    return {
        "total_return_pct": round(total_return_pct, 2),
        "annualized_return_pct": round(annualized_return_pct, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "trade_count": len(trades),
        "win_rate": round(win_rate, 2),
        "equity_curve": equity_curve,
        "trades": trades,
        "start_date": start_date,
        "end_date": end_date,
    }
