"""
test_single_cycle.py - Run a single NanoQuant AI cycle for testing
"""

import logging
from main import NanoQuantAI
from dotenv import load_dotenv
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_cycle.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('TestCycle')


def run_single_cycle():
    """Run one complete cycle for testing"""

    # Load settings from .env
    load_dotenv()

    trading_capital = float(os.getenv('TRADING_CAPITAL', 75))
    max_position_size = float(os.getenv('MAX_POSITION_SIZE', 5))

    logger.info("\n" + "="*60)
    logger.info("TESTING SINGLE CYCLE")
    logger.info("="*60)

    # Initialize bot
    bot = NanoQuantAI(
        trading_capital=trading_capital,
        max_position_size=max_position_size,
        ai_model='claude',
        simulation_mode=True
    )

    # Run Layer 1: Scan candidates
    logger.info("\n\nSTEP 1: Running candidate scan...")
    bot.candidate_pool = bot.layer1_scan_candidates()

    # Run Layer 2 & 3: One complete cycle
    logger.info("\n\nSTEP 2: Running evaluation and trading cycle...")
    bot.run_cycle()

    # Print final portfolio status
    logger.info("\n\n" + "="*60)
    logger.info("FINAL PORTFOLIO STATUS")
    logger.info("="*60)
    logger.info(f"Cash: ${bot.portfolio.cash:.2f}")
    logger.info(f"Initial Cash: ${bot.portfolio.initial_cash:.2f}")

    if bot.portfolio.positions:
        logger.info("\nPositions:")
        for ticker, position in bot.portfolio.positions.items():
            current_price = bot.data_fetcher.get_current_price(ticker)
            value = position['qty'] * current_price if current_price else 0
            logger.info(f"  {ticker}: {position['qty']:.4f} shares @ ${position['avg_price']:.2f} (Value: ${value:.2f})")

    total_value = bot.portfolio.get_total_value(bot.data_fetcher)
    pnl = bot.portfolio.get_pnl(bot.data_fetcher)

    logger.info(f"\nTotal Value: ${total_value:.2f}")
    logger.info(f"P/L: ${pnl:+.2f} ({pnl/bot.portfolio.initial_cash*100:+.1f}%)")

    logger.info("\n" + "="*60)
    logger.info("Trade history saved to trade_history.json")
    logger.info("Full logs saved to test_cycle.log")
    logger.info("="*60 + "\n")


if __name__ == '__main__':
    run_single_cycle()
