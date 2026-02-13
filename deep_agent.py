"""
deep_agent.py - AI-powered deep analysis agent
"""

import logging
import re
from typing import Dict, List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
import os
import json

logger = logging.getLogger('NanoQuant')


def _extract_json(text: str) -> dict:
    """
    Extract JSON from LLM response. Handles:
    - Raw JSON
    - JSON wrapped in markdown code blocks (```json ... ```)
    - Leading/trailing whitespace or extra text
    """
    if not text or not text.strip():
        raise ValueError("Empty response from LLM")

    text = text.strip()

    # Try markdown code block first: ```json ... ``` or ``` ... ```
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if match:
        text = match.group(1).strip()

    # Try to find JSON object {...}
    obj_match = re.search(r'\{[\s\S]*\}', text)
    if obj_match:
        text = obj_match.group(0)

    return json.loads(text)


@dataclass
class TradingDecision:
    """Container for trading decision"""
    action: str  # 'BUY', 'SELL', 'HOLD'
    amount: float  # Dollar amount to trade
    confidence: float  # 0-100
    reasoning: str
    risk_level: str  # 'LOW', 'MEDIUM', 'HIGH'


class DeepAgent:
    """
    AI agent that analyzes chart data and news to make trading decisions
    """

    def __init__(self, model: str = 'claude', max_position_size: float = 5.0):
        """
        Initialize deep agent

        Args:
            model: 'claude' or 'gpt'
            max_position_size: Maximum $ per trade
        """
        load_dotenv()

        self.model = model
        self.max_position_size = max_position_size

        if model == 'claude':
            self.api_key = os.getenv('ANTHROPIC_API_KEY')
            if not self.api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in .env")
        else:
            self.api_key = os.getenv('OPENAI_API_KEY')
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY not found in .env")

    def _build_prompt(
        self,
        ticker: str,
        chart_data: List[Dict],
        news_items: List[Dict],
        trigger_reasons: List[str],
        current_balance: float,
        current_positions: Dict = None,
        learning_summary: str = None,
        quant_indicators: Dict = None,
        current_price: float = None,
    ) -> str:
        """
        Build analysis prompt for LLM

        Args:
            ticker: Stock ticker
            chart_data: List of OHLCV bars
            news_items: List of news headlines
            trigger_reasons: Why this stock was triggered
            current_balance: Available cash
            current_positions: Dict of current holdings
            learning_summary: Summary of past reflections
            current_price: Current market price of ticker (for PnL context on SELL)

        Returns:
            Formatted prompt string
        """
        current_positions = current_positions or {}

        prompt = f"""You are an expert day trader analyzing a small-cap US stock for a potential trade.

{'=' * 60}
{learning_summary if learning_summary else ''}
{'=' * 60}


**Ticker**: {ticker}

**Why This Stock Was Flagged**:
{chr(10).join('- ' + reason for reason in trigger_reasons)}

**Recent Price Action (15-min bars)**:
"""
        # Add chart data
        for i, bar in enumerate(chart_data[-5:]):  # Last 5 bars
            prompt += f"\n{i+1}. Open: ${bar.get('open', 0):.2f}, High: ${bar.get('high', 0):.2f}, Low: ${bar.get('low', 0):.2f}, Close: ${bar.get('close', 0):.2f}, Volume: {bar.get('volume', 0):,.0f}"

        prompt += f"\n\n**Recent News Headlines**:\n"
        if news_items:
            for i, item in enumerate(news_items[:5]):
                prompt += f"\n{i+1}. {item.get('title', 'No title')} ({item.get('time', 'Unknown time')})"
        else:
            prompt += "No recent news available."

        qi = quant_indicators or {}
        if qi:
            prompt += "\n\n**Quant Indicators (15m / 1h / 1d)**:\n"
            tf_labels = {'15m': '15분', '1h': '1시간', '1d': '1일'}
            for tf_key in ('15m', '1h', '1d'):
                tf_data = qi.get(tf_key) if isinstance(qi.get(tf_key), dict) else {}
                if not tf_data:
                    continue
                prompt += f"\n[{tf_labels.get(tf_key, tf_key)}]\n"
                if tf_data.get('rsi') is not None:
                    prompt += f"  - RSI: {tf_data['rsi']:.1f}\n"
                if tf_data.get('sma_20') is not None:
                    prompt += f"  - SMA(20): {tf_data['sma_20']:.2f}\n"
                if tf_data.get('ema_12') is not None:
                    prompt += f"  - EMA(12): {tf_data['ema_12']:.2f}\n"
                if tf_data.get('ema_26') is not None:
                    prompt += f"  - EMA(26): {tf_data['ema_26']:.2f}\n"
                macd_d = tf_data.get('macd')
                if isinstance(macd_d, dict):
                    prompt += f"  - MACD Histogram: {macd_d.get('histogram', 0):.2f}\n"
                bb_d = tf_data.get('bollinger')
                if isinstance(bb_d, dict):
                    prompt += f"  - Bollinger %B: {bb_d.get('pct_b', 0):.2f}\n"
                mom = tf_data.get('momentum')
                if isinstance(mom, (list, tuple)) and len(mom) >= 2:
                    prompt += f"  - Momentum(5): {mom[0]:.2f}%, {'up' if mom[1] > 0 else 'down'}\n"
                if tf_data.get('volume_ratio') is not None:
                    prompt += f"  - Volume ratio: {tf_data['volume_ratio']:.2f}x\n"

        prompt += f"""

**Current Portfolio**:
- Available Cash: ${current_balance:.2f}
- Max Position Size: ${self.max_position_size:.2f}
"""

        if current_positions:
            prompt += "- Current Positions:\n"
            for symbol, data in current_positions.items():
                qty = data.get('qty', 0)
                avg_price = data.get('avg_price', 0)
                line = f"  * {symbol}: {qty} shares, 매수가(평균단가) ${avg_price:.2f}"
                if symbol == ticker and current_price is not None and avg_price and avg_price > 0:
                    pnl_pct = (current_price - avg_price) / avg_price * 100
                    line += f", 현재가 ${current_price:.2f}, 평가손익 {pnl_pct:+.2f}%"
                prompt += line + "\n"
        else:
            prompt += "- No current positions\n"

        prompt += f"""

**Your Task**:
Analyze the above data and make ONE of these decisions:
1. **BUY** - If you see a strong opportunity (specify dollar amount up to ${self.max_position_size:.2f})
2. **SELL** - If you hold this stock and should exit (specify % of position)
3. **HOLD** - If the signal is unclear or risky

**Response Format** (JSON only):
{{
    "action": "BUY|SELL|HOLD",
    "amount": <dollar amount for BUY, or percentage for SELL, or 0 for HOLD>,
    "confidence": <0-100>,
    "reasoning": "<2-3 문장으로 한국어로 결론 근거 설명>",
    "risk_level": "LOW|MEDIUM|HIGH"
}}

**Guidelines**:
- This is small-cap trading with ~$75 total capital
- Only trade if confidence >= 65 (balanced aggression)
- Consider: Is the news catalyst real? Is volume confirming? Is the price action sustainable?
- Multi-timeframe: 1d = trend context, 1h = structure, 15m = entry timing
- Use quant indicators: RSI<30 oversold (반등 후보), RSI>70 overbought; MACD histogram sign = trend; Bollinger %B = position
- **SELL 시**: 매수가 대비 현재가·평가손익을 고려하여 수익실현/손절 판단
- When RSI oversold + news catalyst align, lean toward taking a small position rather than waiting for "perfect" confirmation
- Avoid pump-and-dumps and illiquid stocks; but do not over-wait for perfect signals
- **reasoning** 필드는 반드시 한국어로 작성할 것

Respond with ONLY the JSON object, no other text.
"""
        return prompt

    def analyze(
        self,
        ticker: str,
        chart_data: List[Dict],
        news_items: List[Dict],
        trigger_reasons: List[str],
        current_balance: float,
        current_positions: Dict = None,
        learning_summary: str = None,
        quant_indicators: Dict = None,
        current_price: float = None,
    ) -> TradingDecision:
        """
        Analyze stock and make trading decision

        Args:
            ticker: Stock ticker
            chart_data: OHLCV data
            news_items: News headlines
            trigger_reasons: Why triggered
            current_balance: Available cash
            current_positions: Current holdings
            learning_summary: Summary of past reflections

        Returns:
            TradingDecision object
        """
        prompt = self._build_prompt(
            ticker, chart_data, news_items,
            trigger_reasons, current_balance, current_positions, learning_summary,
            quant_indicators=quant_indicators,
            current_price=current_price,
        )

        # Call LLM API
        try:
            if self.model == 'claude':
                response = self._call_claude(prompt)
            else:
                response = self._call_gpt(prompt)

            # Parse response (handles markdown-wrapped JSON, extra text)
            decision_data = _extract_json(response)

            return TradingDecision(
                action=decision_data.get('action', 'HOLD'),
                amount=float(decision_data.get('amount', 0)),
                confidence=float(decision_data.get('confidence', 0)),
                reasoning=decision_data.get('reasoning', 'No reasoning provided'),
                risk_level=decision_data.get('risk_level', 'UNKNOWN')
            )

        except Exception as e:
            logger.exception("Deep agent analysis failed")
            # Store short message for DB; full details are in logs
            short_msg = "Analysis failed (API or parse error). Check logs for details."
            return TradingDecision(
                action='HOLD',
                amount=0,
                confidence=0,
                reasoning=short_msg,
                risk_level='HIGH'
            )

    def _call_claude(self, prompt: str) -> str:
        """
        Call Claude API

        Args:
            prompt: Analysis prompt

        Returns:
            JSON string response
        """
        try:
            from anthropic import Anthropic

            client = Anthropic(api_key=self.api_key)
            # Use CLAUDE_MODEL from .env; default Haiku (fast/cheap). Sonnet: claude-sonnet-4-5
            model = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5")
            if not prompt or not prompt.strip():
                raise ValueError("Prompt must be non-empty")

            message = client.messages.create(
                model=model,
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt.strip()}
                ]
            )

            text = ""
            for block in (message.content or []):
                if hasattr(block, "text") and block.text:
                    text += block.text
            if not text.strip():
                raise ValueError("Empty response from Claude")
            return text.strip()

        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

    def _call_gpt(self, prompt: str) -> str:
        """
        Call OpenAI GPT API

        Args:
            prompt: Analysis prompt

        Returns:
            JSON string response
        """
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert day trader. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )

            return response.choices[0].message.content

        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")


def test_agent():
    """Test the deep agent (mock mode without API calls)"""
    print("Testing Deep Agent (mock mode)...")

    # Mock data
    chart_data = [
        {'open': 10.0, 'high': 10.5, 'low': 9.8, 'close': 10.3, 'volume': 1_000_000},
        {'open': 10.3, 'high': 10.8, 'low': 10.2, 'close': 10.7, 'volume': 1_500_000},
        {'open': 10.7, 'high': 11.2, 'low': 10.6, 'close': 11.0, 'volume': 2_000_000},
    ]

    news_items = [
        {'title': 'Company announces FDA approval for new drug', 'time': '2 hours ago'},
        {'title': 'Stock surges on breakthrough technology', 'time': '1 hour ago'},
    ]

    trigger_reasons = [
        '[40pts] Price volatility: 3.5%',
        '[40pts] Important news keywords: FDA, approval',
        '[20pts] Volume surge: 2.5x average'
    ]

    # Note: This will fail without API keys, but shows the structure
    try:
        agent = DeepAgent(model='claude', max_position_size=5.0)

        decision = agent.analyze(
            ticker='TEST',
            chart_data=chart_data,
            news_items=news_items,
            trigger_reasons=trigger_reasons,
            current_balance=75.0
        )

        print(f"\nDecision: {decision.action}")
        print(f"Amount: ${decision.amount:.2f}")
        print(f"Confidence: {decision.confidence}%")
        print(f"Risk: {decision.risk_level}")
        print(f"Reasoning: {decision.reasoning}")

    except ValueError as e:
        print(f"\nSkipping API test: {str(e)}")
        print("To test with real API, add ANTHROPIC_API_KEY or OPENAI_API_KEY to .env")


if __name__ == '__main__':
    test_agent()
