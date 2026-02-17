"""
ui/portfolio.py - 포트폴리오 탭 데이터
"""

from util import load_json_file


def load_portfolio(trade_history_path: str, initial_cash: float = 75.0):
    """
    trade_history.json에서 포트폴리오 상태 복원 후 현재가 반영.

    Returns:
        dict with cash, total_value, pnl, pnl_pct, initial_cash, positions, trade_history
        or None if no history
    """
    history = load_json_file(trade_history_path, [])
    if not history or not isinstance(history, list):
        return None

    cash = initial_cash
    positions = {}

    for record in history:
        action = record.get('action')
        ticker = record.get('ticker')
        shares = record.get('shares', 0)
        price = record.get('price', 0)
        amount = record.get('amount', 0)
        if not action or not ticker:
            continue
        if action == 'BUY' and price > 0:
            if ticker in positions:
                cv = positions[ticker]['qty'] * positions[ticker]['avg_price']
                total_qty = positions[ticker]['qty'] + shares
                positions[ticker] = {'qty': total_qty, 'avg_price': (cv + amount) / total_qty}
            else:
                positions[ticker] = {'qty': shares, 'avg_price': price}
            cash -= amount
        elif action == 'SELL':
            if ticker not in positions:
                continue
            positions[ticker]['qty'] -= shares
            if positions[ticker]['qty'] < 0.001:
                del positions[ticker]
            cash += amount

    total_value = cash
    pos_list = []

    try:
        from core import DataFetcher
        fetcher = DataFetcher()
        for ticker, pos in positions.items():
            current_price = fetcher.get_current_price(ticker)
            qty = pos['qty']
            avg_price = pos['avg_price']
            cost = qty * avg_price
            value = (qty * current_price) if current_price else None
            pnl_pct = ((current_price - avg_price) / avg_price * 100) if current_price and avg_price else None
            if value is not None:
                total_value += value
            pos_list.append({
                'ticker': ticker,
                'qty': qty,
                'avg_price': avg_price,
                'current_price': current_price,
                'value': value,
                'pnl_pct': pnl_pct,
            })
    except Exception:
        for ticker, pos in positions.items():
            total_value += pos['qty'] * pos['avg_price']
            pos_list.append({
                'ticker': ticker,
                'qty': pos['qty'],
                'avg_price': pos['avg_price'],
                'current_price': None,
                'value': pos['qty'] * pos['avg_price'],
                'pnl_pct': None,  # DataFetcher 실패 시
            })

    pnl = total_value - initial_cash
    pnl_pct = (pnl / initial_cash * 100) if initial_cash else 0
    trade_log = list(reversed(history)) if history else []

    return {
        'cash': cash,
        'total_value': total_value,
        'pnl': pnl,
        'pnl_pct': pnl_pct,
        'initial_cash': initial_cash,
        'positions': pos_list,
        'trade_history': trade_log,
    }
