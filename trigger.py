"""
trigger.py - Event-driven trigger engine with scoring system
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import pandas as pd


@dataclass
class TriggerScore:
    """Container for trigger scores"""
    price_score: int = 0
    news_score: int = 0
    volume_score: int = 0
    total_score: int = 0
    triggered: bool = False
    reasons: List[str] = None

    def __post_init__(self):
        if self.reasons is None:
            self.reasons = []


class EventTrigger:
    """
    Event-driven trigger engine that scores stocks based on:
    - Price volatility (40 points max)
    - News detection (40 points max)
    - Volume surge (20 points max)

    Threshold: 60+ points triggers deep agent analysis
    """

    # Scoring weights
    PRICE_VOLATILITY_THRESHOLD = 1.0  # 1% change in 15 min (lowered from 3%)
    PRICE_MAX_SCORE = 40

    NEWS_MAX_SCORE = 40

    VOLUME_SURGE_MULTIPLIER = 1.2  # 1.2x average volume (lowered from 2.0x)
    VOLUME_MAX_SCORE = 20

    TRIGGER_THRESHOLD = 25  # Points needed to trigger (lowered from 60)

    # Important news keywords
    IMPORTANT_KEYWORDS = [
        'FDA', 'approval', 'earnings', 'beat', 'miss',
        'acquisition', 'merger', 'buyout', 'CEO',
        'bankruptcy', 'lawsuit', 'investigation',
        'breakthrough', 'patent', 'contract', 'deal',
        'upgrade', 'downgrade', 'halt', 'squeeze'
    ]

    def __init__(self):
        pass

    def calculate_price_score(
        self,
        current_price: float,
        prev_price: float
    ) -> tuple[int, str]:
        """
        Calculate score based on price volatility

        Args:
            current_price: Current stock price
            prev_price: Price from 15 minutes ago

        Returns:
            Tuple of (score, reason)
        """
        if prev_price == 0:
            return 0, "Invalid previous price"

        change_percent = abs((current_price - prev_price) / prev_price) * 100

        if change_percent >= self.PRICE_VOLATILITY_THRESHOLD:
            score = self.PRICE_MAX_SCORE
            reason = f"Price volatility: {change_percent:.2f}% (threshold: {self.PRICE_VOLATILITY_THRESHOLD}%)"
            return score, reason

        # Partial scoring for smaller moves
        if change_percent >= self.PRICE_VOLATILITY_THRESHOLD * 0.5:
            score = int(self.PRICE_MAX_SCORE * 0.5)
            reason = f"Moderate volatility: {change_percent:.2f}%"
            return score, reason

        return 0, f"Low volatility: {change_percent:.2f}%"

    def calculate_news_score(
        self,
        news_detected: bool,
        matched_keywords: List[str] = None
    ) -> tuple[int, str]:
        """
        Calculate score based on news detection

        Args:
            news_detected: Whether news was found
            matched_keywords: List of matched keywords

        Returns:
            Tuple of (score, reason)
        """
        if not news_detected:
            return 0, "No recent news"

        if matched_keywords and len(matched_keywords) > 0:
            # Higher score for important keywords
            score = self.NEWS_MAX_SCORE
            reason = f"Important news keywords: {', '.join(matched_keywords)}"
        else:
            # Partial score for general news
            score = int(self.NEWS_MAX_SCORE * 0.5)
            reason = "General news detected"

        return score, reason

    def calculate_volume_score(
        self,
        current_volume: float,
        average_volume: float
    ) -> tuple[int, str]:
        """
        Calculate score based on volume surge

        Args:
            current_volume: Current period volume
            average_volume: Average volume (e.g., 5-day average)

        Returns:
            Tuple of (score, reason)
        """
        if average_volume == 0:
            return 0, "Invalid average volume"

        volume_ratio = current_volume / average_volume

        if volume_ratio >= self.VOLUME_SURGE_MULTIPLIER:
            score = self.VOLUME_MAX_SCORE
            reason = f"Volume surge: {volume_ratio:.2f}x average (threshold: {self.VOLUME_SURGE_MULTIPLIER}x)"
            return score, reason

        # Partial scoring for smaller surges
        if volume_ratio >= self.VOLUME_SURGE_MULTIPLIER * 0.75:
            score = int(self.VOLUME_MAX_SCORE * 0.5)
            reason = f"Moderate volume increase: {volume_ratio:.2f}x average"
            return score, reason

        return 0, f"Normal volume: {volume_ratio:.2f}x average"

    def evaluate_trigger(
        self,
        ticker: str,
        current_price: float,
        prev_price: float,
        current_volume: float,
        average_volume: float,
        news_detected: bool = False,
        matched_keywords: List[str] = None
    ) -> TriggerScore:
        """
        Evaluate all trigger conditions and return score

        Args:
            ticker: Stock ticker symbol
            current_price: Current price
            prev_price: Price from 15 minutes ago
            current_volume: Current period volume
            average_volume: Average volume baseline
            news_detected: Whether news was found
            matched_keywords: List of matched important keywords

        Returns:
            TriggerScore object with detailed scoring
        """
        reasons = []

        # Calculate individual scores
        price_score, price_reason = self.calculate_price_score(current_price, prev_price)
        if price_score > 0:
            reasons.append(f"[{price_score}pts] {price_reason}")

        news_score, news_reason = self.calculate_news_score(news_detected, matched_keywords)
        if news_score > 0:
            reasons.append(f"[{news_score}pts] {news_reason}")

        volume_score, volume_reason = self.calculate_volume_score(current_volume, average_volume)
        if volume_score > 0:
            reasons.append(f"[{volume_score}pts] {volume_reason}")

        # Calculate total
        total_score = price_score + news_score + volume_score
        triggered = total_score >= self.TRIGGER_THRESHOLD

        return TriggerScore(
            price_score=price_score,
            news_score=news_score,
            volume_score=volume_score,
            total_score=total_score,
            triggered=triggered,
            reasons=reasons
        )

    def batch_evaluate(
        self,
        candidates: List[Dict]
    ) -> List[tuple[str, TriggerScore]]:
        """
        Evaluate multiple stocks and return triggered ones

        Args:
            candidates: List of dicts with stock data
                Required keys: ticker, current_price, prev_price,
                              current_volume, avg_volume
                Optional: news_detected, matched_keywords

        Returns:
            List of (ticker, TriggerScore) tuples sorted by score
        """
        results = []

        for stock in candidates:
            score = self.evaluate_trigger(
                ticker=stock['ticker'],
                current_price=stock['current_price'],
                prev_price=stock['prev_price'],
                current_volume=stock['current_volume'],
                average_volume=stock['avg_volume'],
                news_detected=stock.get('news_detected', False),
                matched_keywords=stock.get('matched_keywords', [])
            )
            results.append((stock['ticker'], score))

        # Sort by total score descending
        results.sort(key=lambda x: x[1].total_score, reverse=True)

        return results

    def get_triggered_stocks(
        self,
        candidates: List[Dict]
    ) -> List[tuple[str, TriggerScore]]:
        """
        Get only stocks that meet the trigger threshold

        Args:
            candidates: List of stock data dicts

        Returns:
            List of (ticker, TriggerScore) for triggered stocks only
        """
        all_results = self.batch_evaluate(candidates)
        return [(ticker, score) for ticker, score in all_results if score.triggered]


def test_trigger():
    """Test the trigger engine"""
    trigger = EventTrigger()

    # Test case 1: High volatility + news
    print("Test 1: High volatility + important news")
    score1 = trigger.evaluate_trigger(
        ticker='AAPL',
        current_price=150.0,
        prev_price=145.0,  # 3.4% increase
        current_volume=50_000_000,
        average_volume=30_000_000,  # 1.67x volume
        news_detected=True,
        matched_keywords=['earnings', 'beat']
    )
    print(f"  Total: {score1.total_score} points | Triggered: {score1.triggered}")
    for reason in score1.reasons:
        print(f"    {reason}")

    # Test case 2: Volume surge only
    print("\nTest 2: Volume surge only")
    score2 = trigger.evaluate_trigger(
        ticker='TSLA',
        current_price=200.0,
        prev_price=199.0,  # 0.5% change
        current_volume=100_000_000,
        average_volume=40_000_000,  # 2.5x volume
        news_detected=False
    )
    print(f"  Total: {score2.total_score} points | Triggered: {score2.triggered}")
    for reason in score2.reasons:
        print(f"    {reason}")

    # Test case 3: Batch evaluation
    print("\nTest 3: Batch evaluation")
    candidates = [
        {
            'ticker': 'NVDA',
            'current_price': 500.0,
            'prev_price': 485.0,  # 3.09%
            'current_volume': 60_000_000,
            'avg_volume': 50_000_000,
            'news_detected': True,
            'matched_keywords': ['breakthrough']
        },
        {
            'ticker': 'AMD',
            'current_price': 100.0,
            'prev_price': 99.0,  # 1%
            'current_volume': 20_000_000,
            'avg_volume': 20_000_000,
            'news_detected': False
        }
    ]

    triggered = trigger.get_triggered_stocks(candidates)
    print(f"  Triggered stocks: {len(triggered)}")
    for ticker, score in triggered:
        print(f"    {ticker}: {score.total_score} points")


if __name__ == '__main__':
    test_trigger()
