"""
core/trigger.py - Event-driven trigger engine with scoring system
"""

import os
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

    PRICE_VOLATILITY_THRESHOLD = 2.0
    PRICE_MAX_SCORE = 40
    NEWS_MAX_SCORE = 40
    VOLUME_SURGE_MULTIPLIER = 1.5
    VOLUME_MAX_SCORE = 20
    TRIGGER_THRESHOLD = 25

    IMPORTANT_KEYWORDS = [
        'FDA', 'approval', 'earnings', 'beat', 'miss',
        'acquisition', 'merger', 'buyout', 'CEO',
        'bankruptcy', 'lawsuit', 'investigation',
        'breakthrough', 'patent', 'contract', 'deal',
        'upgrade', 'downgrade', 'halt', 'squeeze'
    ]

    def __init__(self):
        self.PRICE_VOLATILITY_THRESHOLD = float(os.environ.get('PRICE_VOLATILITY_THRESHOLD', 2.0))
        self.PRICE_MAX_SCORE = int(os.environ.get('PRICE_MAX_SCORE', 40))
        self.NEWS_MAX_SCORE = int(os.environ.get('NEWS_MAX_SCORE', 40))
        self.VOLUME_SURGE_MULTIPLIER = float(os.environ.get('VOLUME_SURGE_MULTIPLIER', 1.5))
        self.VOLUME_MAX_SCORE = int(os.environ.get('VOLUME_MAX_SCORE', 20))
        self.TRIGGER_THRESHOLD = int(os.environ.get('TRIGGER_THRESHOLD', 25))

    def calculate_price_score(self, current_price: float, prev_price: float) -> tuple[int, str]:
        if prev_price == 0:
            return 0, "Invalid previous price"
        change_percent = abs((current_price - prev_price) / prev_price) * 100
        if change_percent >= self.PRICE_VOLATILITY_THRESHOLD:
            return self.PRICE_MAX_SCORE, f"Price volatility: {change_percent:.2f}% (threshold: {self.PRICE_VOLATILITY_THRESHOLD}%)"
        if change_percent >= self.PRICE_VOLATILITY_THRESHOLD * 0.5:
            return int(self.PRICE_MAX_SCORE * 0.5), f"Moderate volatility: {change_percent:.2f}%"
        return 0, f"Low volatility: {change_percent:.2f}%"

    def calculate_news_score(self, news_detected: bool, matched_keywords: List[str] = None) -> tuple[int, str]:
        if not news_detected:
            return 0, "No recent news"
        if matched_keywords and len(matched_keywords) > 0:
            return self.NEWS_MAX_SCORE, f"Important news keywords: {', '.join(matched_keywords)}"
        return int(self.NEWS_MAX_SCORE * 0.5), "General news detected"

    def calculate_volume_score(self, current_volume: float, average_volume: float) -> tuple[int, str]:
        if average_volume == 0:
            return 0, "Invalid average volume"
        volume_ratio = current_volume / average_volume
        if volume_ratio >= self.VOLUME_SURGE_MULTIPLIER:
            return self.VOLUME_MAX_SCORE, f"Volume surge: {volume_ratio:.2f}x average (threshold: {self.VOLUME_SURGE_MULTIPLIER}x)"
        if volume_ratio >= self.VOLUME_SURGE_MULTIPLIER * 0.75:
            return int(self.VOLUME_MAX_SCORE * 0.5), f"Moderate volume increase: {volume_ratio:.2f}x average"
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
        reasons = []
        price_score, price_reason = self.calculate_price_score(current_price, prev_price)
        if price_score > 0:
            reasons.append(f"[{price_score}pts] {price_reason}")
        news_score, news_reason = self.calculate_news_score(news_detected, matched_keywords)
        if news_score > 0:
            reasons.append(f"[{news_score}pts] {news_reason}")
        volume_score, volume_reason = self.calculate_volume_score(current_volume, average_volume)
        if volume_score > 0:
            reasons.append(f"[{volume_score}pts] {volume_reason}")
        total_score = price_score + news_score + volume_score
        triggered = total_score >= self.TRIGGER_THRESHOLD
        return TriggerScore(
            price_score=price_score, news_score=news_score, volume_score=volume_score,
            total_score=total_score, triggered=triggered, reasons=reasons
        )

    def batch_evaluate(self, candidates: List[Dict]) -> List[tuple[str, TriggerScore]]:
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
        results.sort(key=lambda x: x[1].total_score, reverse=True)
        return results

    def get_triggered_stocks(self, candidates: List[Dict]) -> List[tuple[str, TriggerScore]]:
        all_results = self.batch_evaluate(candidates)
        return [(ticker, score) for ticker, score in all_results if score.triggered]
