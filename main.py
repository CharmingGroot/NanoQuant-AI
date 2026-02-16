"""
main.py - Main orchestration loop for NanoQuant AI (yfinance + Simulation Mode)
"""

import time
from datetime import datetime
from typing import List, Dict
import schedule
import logging
from dotenv import load_dotenv
import os
import json

from data_fetcher import DataFetcher
from scraper import StockScraper
from trigger import EventTrigger
from deep_agent import DeepAgent, TradingDecision
from database import TradingDatabase
from quant_rules import compute_all_multi
from missed_profit import run_decision_followup_cycle


def _serialize_quant_multi(quant_multi: dict) -> dict:
    """다중 타임프레임 quant_indicators를 JSON/DB 저장 가능한 형태로 직렬화"""
    out = {}
    for tf, indicators in (quant_multi or {}).items():
        if not indicators:
            continue
        ser = {}
        for k, v in indicators.items():
            if v is None:
                continue
            ser[k] = list(v) if isinstance(v, tuple) else v
        out[tf] = ser
    return out


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nanoquant.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('NanoQuant')


class Portfolio:
    """Simple portfolio tracker for simulation mode"""

    def __init__(self, initial_cash: float = 75.0):
        self.cash = initial_cash
        self.initial_cash = initial_cash
        self.positions = {}  # {ticker: {'qty': shares, 'avg_price': price}}
        self.trade_history = []

    def buy(self, ticker: str, amount: float, price: float):
        """Execute buy order"""
        shares = amount / price

        if ticker in self.positions:
            # Average down/up
            current_value = self.positions[ticker]['qty'] * self.positions[ticker]['avg_price']
            new_value = amount
            total_qty = self.positions[ticker]['qty'] + shares

            self.positions[ticker] = {
                'qty': total_qty,
                'avg_price': (current_value + new_value) / total_qty
            }
        else:
            self.positions[ticker] = {'qty': shares, 'avg_price': price}

        self.cash -= amount
        self.trade_history.append({
            'timestamp': datetime.now().isoformat(),
            'action': 'BUY',
            'ticker': ticker,
            'shares': shares,
            'price': price,
            'amount': amount
        })

    def sell(self, ticker: str, percentage: float, price: float):
        """Execute sell order"""
        if ticker not in self.positions:
            return 0

        shares_to_sell = self.positions[ticker]['qty'] * (percentage / 100)
        amount = shares_to_sell * price

        self.positions[ticker]['qty'] -= shares_to_sell

        if self.positions[ticker]['qty'] < 0.001:
            del self.positions[ticker]

        self.cash += amount
        self.trade_history.append({
            'timestamp': datetime.now().isoformat(),
            'action': 'SELL',
            'ticker': ticker,
            'shares': shares_to_sell,
            'price': price,
            'amount': amount
        })

        return amount

    def get_total_value(self, data_fetcher: DataFetcher) -> float:
        """Calculate total portfolio value"""
        total = self.cash

        for ticker, position in self.positions.items():
            current_price = data_fetcher.get_current_price(ticker)
            if current_price:
                total += position['qty'] * current_price

        return total

    def get_pnl(self, data_fetcher: DataFetcher) -> float:
        """Get profit/loss"""
        return self.get_total_value(data_fetcher) - self.initial_cash

    def save_history(self, filename: str = 'trade_history.json'):
        """Save trade history to file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.trade_history, f, indent=2)

    def load_from_history(self, filename: str = 'trade_history.json') -> bool:
        """
        Restore portfolio state from trade_history.json (cash + positions).
        Replays each trade in order. Call after __init__ on startup.

        Returns:
            True if loaded and replayed, False if file missing or empty/invalid.
        """
        if not os.path.exists(filename):
            return False
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                history = json.load(f)
            if not history or not isinstance(history, list):
                return False

            # Reset to initial state, then replay (do not append to trade_history during replay)
            self.cash = self.initial_cash
            self.positions = {}

            for record in history:
                action = record.get('action')
                ticker = record.get('ticker')
                shares = record.get('shares', 0)
                price = record.get('price', 0)
                amount = record.get('amount', 0)
                if not action or not ticker:
                    continue
                if action == 'BUY' and price > 0:
                    if ticker in self.positions:
                        current_value = self.positions[ticker]['qty'] * self.positions[ticker]['avg_price']
                        total_qty = self.positions[ticker]['qty'] + shares
                        self.positions[ticker] = {
                            'qty': total_qty,
                            'avg_price': (current_value + amount) / total_qty
                        }
                    else:
                        self.positions[ticker] = {'qty': shares, 'avg_price': price}
                    self.cash -= amount
                elif action == 'SELL':
                    if ticker not in self.positions:
                        continue
                    self.positions[ticker]['qty'] -= shares
                    if self.positions[ticker]['qty'] < 0.001:
                        del self.positions[ticker]
                    self.cash += amount

            self.trade_history = history
            return True
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            logger.warning(f"Could not load portfolio from {filename}: {e}")
            return False


class NanoQuantAI:
    """
    Main orchestrator for the NanoQuant AI trading system

    Architecture:
    - Layer 1: Quant Scanner (daily/hourly) - selects 50 small-cap candidates
    - Layer 2: Event-Driven Trigger (every 15 min) - scores candidates
    - Layer 3: Deep Agent (on trigger) - LLM analyzes and makes decisions

    Mode: SIMULATION (no real trades, uses yfinance for data)
    """

    def __init__(
        self,
        trading_capital: float = 75.0,
        max_position_size: float = 5.0,
        ai_model: str = 'claude',
        simulation_mode: bool = True,
        scan_only: bool = False,
        use_news_for_trading: bool = True
    ):
        """
        Initialize NanoQuant AI

        Args:
            trading_capital: Total capital in USD
            max_position_size: Max $ per position
            ai_model: 'claude' or 'gpt'
            simulation_mode: Run in simulation (no real trades)
            scan_only: If True, run only Layer 1+2 (no LLM, no trades, no DB)
            use_news_for_trading: If True, fetch news and use in trigger/LLM; if False, exclude news
        """
        load_dotenv()

        self.trading_capital = trading_capital
        self.max_position_size = max_position_size
        self.simulation_mode = simulation_mode
        self.scan_only = scan_only
        self.use_news_for_trading = use_news_for_trading

        # Initialize components
        logger.info("Initializing NanoQuant AI components...")

        try:
            self.data_fetcher = DataFetcher()
            self.trigger_engine = EventTrigger()

            if scan_only:
                self.deep_agent = None
                self.db = None
                self.portfolio = None
                logger.info("[OK] Scan-only mode: Layer 1+2 only (no LLM/DB)")
            else:
                self.deep_agent = DeepAgent(model=ai_model, max_position_size=max_position_size)
                self.db = TradingDatabase('nanoquant_v1.db')
                if simulation_mode:
                    self.portfolio = Portfolio(initial_cash=trading_capital)
                    _history_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'trade_history.json')
                    if self.portfolio.load_from_history(_history_path):
                        logger.info(
                            "Portfolio restored from trade_history.json "
                            "(cash=%.2f, positions=%s)",
                            self.portfolio.cash,
                            list(self.portfolio.positions.keys()) or "none"
                        )
                else:
                    raise NotImplementedError("Live trading not yet implemented. Set simulation_mode=True")

            # Candidate pool (refreshed daily/hourly)
            self.candidate_pool: List[str] = []

            logger.info("[OK] All components initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize: {str(e)}")
            raise

    def layer1_scan_candidates(self) -> List[str]:
        """
        Layer 1: Quant Scanner

        Scans universe of US small-cap stocks and selects top 50 candidates
        based on low PBR/PER and volume

        Returns:
            List of ticker symbols
        """
        logger.info("=" * 60)
        logger.info("LAYER 1: Scanning for small-cap candidates...")

        candidates = self.data_fetcher.scan_small_caps(limit=50)

        logger.info(f"[OK] Selected {len(candidates)} candidates: {', '.join(candidates)}")
        logger.info("=" * 60)

        return candidates

    def layer2_evaluate_triggers(self) -> List[tuple[str, any]]:
        """
        Layer 2: Event-Driven Trigger

        Evaluates all candidates using the scoring system:
        - Price volatility (40 pts)
        - News detection (40 pts)
        - Volume surge (20 pts)

        Returns:
            List of (ticker, TriggerScore) for triggered stocks
        """
        logger.info("\n" + "=" * 60)
        logger.info(f"LAYER 2: Evaluating triggers ({datetime.now().strftime('%H:%M:%S')})")

        if not self.candidate_pool:
            logger.warning("No candidates in pool. Running Layer 1 scan...")
            self.candidate_pool = self.layer1_scan_candidates()

        triggered_stocks = []
        scraper = StockScraper(headless=True) if self.use_news_for_trading else None
        if scraper:
            scraper.start()

        try:
            stock_data = []
            _empty_news = {'found': False, 'matches': []}

            for ticker in self.candidate_pool:
                logger.info(f"  Analyzing {ticker}...")

                # Get market data
                snapshot = self.data_fetcher.get_stock_snapshot(ticker)

                if not snapshot['data_available']:
                    logger.warning(f"    [X] No data available for {ticker}")
                    continue

                # Get news data (skip when USE_NEWS_FOR_TRADING=0)
                if self.use_news_for_trading and scraper:
                    news_items = scraper.get_stock_news(ticker, max_articles=10)
                    news_result = scraper.check_keywords_in_news(
                        ticker,
                        self.trigger_engine.IMPORTANT_KEYWORDS,
                        news_items=news_items
                    )
                else:
                    news_items = []
                    news_result = _empty_news

                bars_dict = snapshot.get('bars_dict', {
                    '15m': snapshot.get('bars_15m', snapshot.get('bars', [])),
                    '1h': snapshot.get('bars_1h', []),
                    '1d': snapshot.get('bars_1d', []),
                })
                quant_multi = compute_all_multi(bars_dict)
                quant_serial = _serialize_quant_multi(quant_multi)

                stock_data.append({
                    'ticker': ticker,
                    'current_price': snapshot['current_price'],
                    'prev_price': snapshot['prev_price'],
                    'current_volume': snapshot['current_volume'],
                    'avg_volume': snapshot['avg_volume'],
                    'bars': bars_dict.get('15m', snapshot.get('bars', [])),
                    'quant_indicators': quant_serial,
                    'news_detected': news_result['found'],
                    'matched_keywords': news_result['matches'],
                    'news_items': news_items
                })

            # Evaluate triggers
            triggered = self.trigger_engine.get_triggered_stocks(stock_data)

            logger.info(f"\n[OK] Triggered stocks: {len(triggered)}/{len(stock_data)}")

            for ticker, score in triggered:
                logger.info(f"\n  {ticker} - {score.total_score} points (TRIGGERED)")
                for reason in score.reasons:
                    logger.info(f"    {reason}")

                # Find corresponding stock data
                stock_info = next((s for s in stock_data if s['ticker'] == ticker), None)
                if stock_info:
                    triggered_stocks.append((ticker, score, stock_info))

        finally:
            if scraper:
                scraper.close()

        logger.info("=" * 60)
        return triggered_stocks

    def layer3_deep_analysis(self, ticker: str, score: any, stock_info: Dict) -> TradingDecision:
        """
        Layer 3: Deep Agent Analysis

        Uses LLM to analyze chart + news and make trading decision

        Args:
            ticker: Stock ticker
            score: TriggerScore object
            stock_info: Dict with stock data

        Returns:
            TradingDecision object
        """
        logger.info(f"\n{'=' * 60}")
        logger.info(f"LAYER 3: Deep analysis for {ticker}")

        # Get current balance and positions
        current_balance = self.portfolio.cash
        position_dict = {
            t: {'qty': p['qty'], 'avg_price': p['avg_price']}
            for t, p in self.portfolio.positions.items()
        }

        # Get learning summary from past 사후 추적 (decision_followups)
        learning_summary = self.db.get_learning_summary(limit=5)

        # Run deep agent (current_price 전달: SELL 시 매수가 대비 손익률 판단용)
        decision = self.deep_agent.analyze(
            ticker=ticker,
            chart_data=stock_info.get('bars', []),
            news_items=stock_info.get('news_items', []),
            trigger_reasons=score.reasons,
            current_balance=current_balance,
            current_positions=position_dict,
            learning_summary=learning_summary,
            quant_indicators=stock_info.get('quant_indicators', {}),
            current_price=stock_info.get('current_price'),
            use_news=self.use_news_for_trading,
        )

        logger.info(f"\n  Decision: {decision.action}")
        logger.info(f"  Amount: ${decision.amount:.2f}")
        logger.info(f"  Confidence: {decision.confidence}%")
        logger.info(f"  Risk: {decision.risk_level}")
        logger.info(f"  Reasoning: {decision.reasoning}")

        # Log decision to database (사유 근거 + 퀀트 지표 포함)
        news_items = stock_info.get('news_items', [])
        metadata = {
            'trigger_reasons': score.reasons,
            'news_headlines': [{'title': n.get('title', ''), 'time': n.get('time', ''), 'link': n.get('link', '')} for n in news_items],
            'news_count': len(news_items),
            'matched_keywords': stock_info.get('matched_keywords', []),
            'current_price': stock_info.get('current_price'),
            'prev_price': stock_info.get('prev_price'),
            'volume_ratio': round(stock_info.get('current_volume', 0) / max(stock_info.get('avg_volume', 1), 1), 2) if stock_info.get('avg_volume') else None,
            'quant_indicators': stock_info.get('quant_indicators', {}),
        }
        decision_id = self.db.log_decision(
            ticker=ticker,
            action=decision.action,
            price=stock_info.get('current_price', 0),
            amount=decision.amount,
            confidence=decision.confidence,
            risk_level=decision.risk_level,
            reasoning=decision.reasoning,
            trigger_score=score.total_score,
            metadata=metadata,
        )

        if decision_id > 0:
            logger.info(f"  [OK] Decision logged to database (ID: {decision_id})")
        else:
            logger.warning(f"  [X] Failed to log decision to database")

        logger.info("=" * 60)

        return decision

    def execute_trade(self, ticker: str, decision: TradingDecision, current_price: float):
        """
        Execute trading decision (simulation mode)

        Args:
            ticker: Stock ticker
            decision: TradingDecision object
            current_price: Current stock price
        """
        if decision.action == 'HOLD':
            logger.info(f"  No trade executed for {ticker} (대기)")
            return

        confidence_threshold = float(os.getenv('CONFIDENCE_THRESHOLD', 65))
        if decision.confidence < confidence_threshold:
            logger.warning(f"  Skipping trade for {ticker} (confidence {decision.confidence}% < {confidence_threshold}%)")
            return

        try:
            if decision.action == 'BUY':
                # Check if we have enough cash
                if self.portfolio.cash < decision.amount:
                    logger.warning(f"  Insufficient cash: ${self.portfolio.cash:.2f} < ${decision.amount:.2f}")
                    return

                self.portfolio.buy(ticker, decision.amount, current_price)
                logger.info(f"  [OK] [SIMULATION] BUY: {ticker} ${decision.amount:.2f} @ ${current_price:.2f}")

            elif decision.action == 'SELL':
                if ticker not in self.portfolio.positions:
                    logger.warning(f"  No position to sell for {ticker}")
                    return

                amount_sold = self.portfolio.sell(ticker, decision.amount, current_price)
                logger.info(f"  [OK] [SIMULATION] SELL: {ticker} {decision.amount}% @ ${current_price:.2f} (${amount_sold:.2f})")

            # Log portfolio status
            total_value = self.portfolio.get_total_value(self.data_fetcher)
            pnl = self.portfolio.get_pnl(self.data_fetcher)
            logger.info(f"  Portfolio: Cash=${self.portfolio.cash:.2f} | Total=${total_value:.2f} | P/L={pnl:+.2f} ({pnl/self.portfolio.initial_cash*100:+.1f}%)")

        except Exception as e:
            logger.error(f"  [X] Failed to execute trade for {ticker}: {str(e)}")

    def run_decision_followup_cycle(self):
        """
        모든 판단(BUY/SELL/HOLD)의 사후 추적 (가격, 옳고그름, LLM 학습메모)
        리플렉션 로직 통합
        """
        try:
            logger.info("\n\n" + "=" * 60)
            logger.info(f"DECISION FOLLOWUP CYCLE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 60)

            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nanoquant_v1.db')
            n = run_decision_followup_cycle(db_path=db_path, min_hours_ago=24, max_followups=30)

            logger.info(f"[OK] Decision followup cycle completed: {n} followups processed\n")
        except Exception as e:
            logger.error(f"Error in decision followup cycle: {str(e)}", exc_info=True)

    def run_cycle(self):
        """
        Run one complete 15-minute cycle

        Flow:
        1. Evaluate triggers for all candidates (Layer 2)
        2. For each triggered stock, run deep analysis (Layer 3)
        3. Execute trades based on agent decisions
        """
        logger.info("\n\n" + "=" * 60)
        logger.info(f"STARTING NEW CYCLE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)

        try:
            # Layer 2: Evaluate triggers
            triggered_stocks = self.layer2_evaluate_triggers()

            if not triggered_stocks:
                logger.info("\n[OK] No stocks triggered this cycle")
                return

            if self.scan_only:
                logger.info("\n[SCAN ONLY] Layer 1+2 complete. Skipping Layer 3 (no LLM, no trades).")
                return

            # Layer 3: Deep analysis and execution
            for ticker, score, stock_info in triggered_stocks:
                decision = self.layer3_deep_analysis(ticker, score, stock_info)

                current_price = stock_info.get('current_price')
                if current_price:
                    self.execute_trade(ticker, decision, current_price)

                # Rate limiting (avoid API spam)
                time.sleep(2)

            # Save trade history (프로젝트 루트 기준, db_viewer와 동일 경로)
            self.portfolio.save_history(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'trade_history.json'))

            logger.info(f"\n[OK] Cycle completed at {datetime.now().strftime('%H:%M:%S')}")

        except Exception as e:
            logger.error(f"Error in cycle: {str(e)}", exc_info=True)

    def start(self):
        """
        Start the main trading loop

        Schedule:
        - Layer 1 scan: Daily at market open (9:30 AM ET) and every 4 hours
        - Layer 2+3: Every 15 minutes during market hours
        """
        logger.info("\n" + "=" * 60)
        logger.info("NANOQUANT AI STARTING")
        logger.info(f"Capital: ${self.trading_capital}")
        logger.info(f"Max Position: ${self.max_position_size}")
        logger.info(f"Mode: {'SIMULATION' if self.simulation_mode else 'LIVE TRADING'}")
        logger.info(f"News for trading: {'ON' if self.use_news_for_trading else 'OFF'}")
        if self.scan_only:
            logger.info("Scan Only: Layer 1+2 only (no LLM, no trades)")
        logger.info("=" * 60)

        # Initial scan
        self.candidate_pool = self.layer1_scan_candidates()

        if self.scan_only:
            # Run Layer 2 once and exit
            self.run_cycle()
            logger.info("\n[SCAN ONLY] Done. Exiting.\n")
            return

        # Schedule tasks
        schedule.every(4).hours.do(lambda: setattr(self, 'candidate_pool', self.layer1_scan_candidates()))
        schedule.every(15).minutes.do(self.run_cycle)

        # Schedule 판단 사후 추적 (가격 + LLM 학습메모, 07:00)
        schedule.every().day.at("07:00").do(self.run_decision_followup_cycle)

        # Run first cycle immediately
        self.run_cycle()

        # Main loop
        logger.info("\n[SCHEDULER] Running every 15 minutes...\n")
        logger.info("   - Trading cycle: Every 15 minutes")
        logger.info("   - Decision followup (판단 사후 추적 + 학습): Daily at 07:00\n")

        while True:
            schedule.run_pending()
            time.sleep(60)


def main():
    """Entry point"""
    # Load settings from .env
    load_dotenv()

    trading_capital = float(os.getenv('TRADING_CAPITAL', 75))
    max_position_size = float(os.getenv('MAX_POSITION_SIZE', 5))
    scan_only = os.getenv('SCAN_ONLY', '0').lower() in ('1', 'true', 'yes')
    use_news_for_trading = os.getenv('USE_NEWS_FOR_TRADING', '1').lower() in ('1', 'true', 'yes')

    # Initialize and start
    bot = NanoQuantAI(
        trading_capital=trading_capital,
        max_position_size=max_position_size,
        ai_model='claude',  # or 'gpt'
        simulation_mode=True,  # Always use simulation mode for safety
        scan_only=scan_only,
        use_news_for_trading=use_news_for_trading
    )

    bot.start()


if __name__ == '__main__':
    main()
