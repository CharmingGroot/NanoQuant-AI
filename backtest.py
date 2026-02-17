"""
backtest.py - 단순 백테스트: trade_history.json 기반 수익률·MDD·회전율·승률 계산

PRD: docs/PRD-position-sizing-stop-take-backtest.md
"""

import os
import json
import argparse
from typing import List, Dict, Any
from dataclasses import dataclass, field

from util import load_json_file, path_for


@dataclass
class Position:
    qty: float
    avg_price: float
    cost_basis: float


def load_trade_history(path: str = None) -> List[Dict]:
    """trade_history.json 로드"""
    if path is None:
        path = path_for('trade_history.json')
    data = load_json_file(path, [])
    return data if isinstance(data, list) else []


def run_backtest(
    trades: List[Dict],
    initial_cash: float,
) -> Dict[str, Any]:
    """
    거래 기록을 순차 재생하여 수익률·MDD·회전율·승률 계산.

    Returns:
        {
            'initial_cash': float,
            'final_cash': float,
            'final_positions_value': float,
            'total_return_pct': float,
            'mdd_pct': float,
            'turnover': float,
            'trade_count': int,
            'win_count': int,
            'loss_count': int,
            'win_rate_pct': float,
            'equity_curve': [(ts, equity), ...],
        }
    """
    cash = initial_cash
    positions: Dict[str, Position] = {}
    equity_curve: List[tuple] = []
    total_traded = 0.0
    win_count = 0
    loss_count = 0

    def _equity() -> float:
        return cash + sum(p.cost_basis for p in positions.values())

    for t in trades:
        action = (t.get('action') or '').upper()
        ticker = (t.get('ticker') or '').strip()
        price = float(t.get('price', 0))
        amount = float(t.get('amount', 0))
        shares = float(t.get('shares', 0))
        ts = t.get('timestamp', '')

        if not ticker or price <= 0:
            continue

        if action == 'BUY':
            total_traded += amount
            if amount <= 0 or shares <= 0:
                continue
            cost = amount
            cash -= cost
            if ticker in positions:
                p = positions[ticker]
                new_qty = p.qty + shares
                new_cost = p.cost_basis + cost
                positions[ticker] = Position(qty=new_qty, avg_price=new_cost / new_qty, cost_basis=new_cost)
            else:
                positions[ticker] = Position(qty=shares, avg_price=price, cost_basis=cost)

        elif action == 'SELL':
            total_traded += amount
            if ticker not in positions or shares <= 0:
                continue
            p = positions[ticker]
            cost_sold = p.cost_basis * (shares / p.qty)
            pnl = amount - cost_sold
            if pnl > 0:
                win_count += 1
            elif pnl < 0:
                loss_count += 1

            cash += amount
            p.qty -= shares
            p.cost_basis -= cost_sold
            if p.qty < 1e-9:
                del positions[ticker]
            else:
                p.avg_price = p.cost_basis / p.qty if p.qty else 0

        equity_curve.append((ts, _equity()))

    final_cash = cash
    final_positions_value = sum(p.cost_basis for p in positions.values())
    final_equity = final_cash + final_positions_value

    total_return_pct = (final_equity - initial_cash) / initial_cash * 100 if initial_cash else 0

    # MDD
    peak = initial_cash
    mdd_pct = 0.0
    for _, eq in equity_curve:
        if eq > peak:
            peak = eq
        if peak > 0:
            dd = (peak - eq) / peak * 100
            if dd > mdd_pct:
                mdd_pct = dd

    # Turnover: sum(|매수|+|매도|) / 2 / 평균 자산
    avg_equity = (initial_cash + final_equity) / 2 if equity_curve else initial_cash
    turnover = (total_traded / avg_equity) if avg_equity > 0 else 0

    trade_count = len([t for t in trades if (t.get('action') or '').upper() in ('BUY', 'SELL')])
    closed_trades = win_count + loss_count
    win_rate_pct = (win_count / closed_trades * 100) if closed_trades > 0 else 0

    return {
        'initial_cash': initial_cash,
        'final_cash': final_cash,
        'final_positions_value': final_positions_value,
        'final_equity': final_equity,
        'total_return_pct': round(total_return_pct, 2),
        'mdd_pct': round(mdd_pct, 2),
        'turnover': round(turnover, 2),
        'trade_count': trade_count,
        'win_count': win_count,
        'loss_count': loss_count,
        'win_rate_pct': round(win_rate_pct, 1),
        'equity_curve': equity_curve,
    }


def main():
    parser = argparse.ArgumentParser(description='NanoQuant 단순 백테스트')
    parser.add_argument(
        '--history',
        default='trade_history.json',
        help='trade_history.json 경로',
    )
    parser.add_argument(
        '--initial-cash',
        type=float,
        default=None,
        help='초기 자산 (USD). 미지정 시 TRADING_CAPITAL 환경변수 또는 75 사용',
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='JSON 형태로만 출력',
    )
    args = parser.parse_args()

    initial = args.initial_cash
    if initial is None:
        initial = float(os.getenv('TRADING_CAPITAL', 75))

    path = path_for(args.history) if args.history == 'trade_history.json' else args.history
    trades = load_trade_history(path)
    if not trades:
        print(f"거래 기록 없음: {args.history}")
        return 1

    result = run_backtest(trades, initial)

    if args.json:
        out = {k: v for k, v in result.items() if k != 'equity_curve'}
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    print("=" * 50)
    print("NanoQuant 백테스트 결과")
    print("=" * 50)
    print(f"초기 자산:     ${result['initial_cash']:.2f}")
    print(f"최종 현금:     ${result['final_cash']:.2f}")
    print(f"미청산 평가:   ${result['final_positions_value']:.2f}")
    print(f"최종 평가총액: ${result['final_equity']:.2f}")
    print("-" * 50)
    print(f"총 수익률:     {result['total_return_pct']:+.2f}%")
    print(f"최대 낙폭:     {result['mdd_pct']:.2f}%")
    print(f"회전율:        {result['turnover']:.2f}x")
    print(f"거래 건수:     {result['trade_count']}")
    print(f"승/패:         {result['win_count']} / {result['loss_count']}")
    print(f"승률:          {result['win_rate_pct']:.1f}%")
    print("=" * 50)
    return 0


if __name__ == '__main__':
    exit(main())
