"""
reflection.py - Self-reflection system for analyzing past decisions
"""

from typing import List, Dict
from datetime import datetime, timedelta
import json

from database import TradingDatabase
from data_fetcher import DataFetcher
from deep_agent import DeepAgent


class ReflectionEngine:
    """
    Self-reflection system that evaluates past trading decisions
    and generates insights for improvement
    """

    def __init__(
        self,
        db_path: str = 'nanoquant_v1.db',
        ai_model: str = 'claude'
    ):
        """
        Initialize reflection engine

        Args:
            db_path: Path to database
            ai_model: AI model to use for reflection
        """
        self.db = TradingDatabase(db_path)
        self.data_fetcher = DataFetcher()
        self.ai_model = ai_model

        # Initialize AI client for reflection
        try:
            self.deep_agent = DeepAgent(model=ai_model, max_position_size=5.0)
        except:
            print("Warning: AI model not initialized. Reflection will use rule-based analysis only.")
            self.deep_agent = None

    def evaluate_decision(
        self,
        decision: Dict,
        hours_elapsed: int = 24
    ) -> Dict:
        """
        Evaluate a single past decision

        Args:
            decision: Decision record from database
            hours_elapsed: Hours to wait before evaluation

        Returns:
            Evaluation results dict
        """
        ticker = decision['ticker']
        action = decision['action']
        decision_price = decision['price']
        decision_time = datetime.fromisoformat(decision['timestamp'])

        # Get current price
        try:
            current_price = self.data_fetcher.get_current_price(ticker)

            if not current_price:
                return {
                    'success': False,
                    'error': f'Could not fetch current price for {ticker}'
                }

            # Calculate profit/loss
            if action == 'BUY':
                profit_loss = ((current_price - decision_price) / decision_price) * 100
                is_success = profit_loss > 0
            elif action == 'SELL':
                # For SELL, success means price went down after selling
                profit_loss = ((decision_price - current_price) / decision_price) * 100
                is_success = profit_loss > 0
            else:
                # HOLD - evaluate if staying out was correct
                profit_loss = 0
                is_success = abs((current_price - decision_price) / decision_price) < 0.02

            return {
                'success': True,
                'ticker': ticker,
                'action': action,
                'decision_price': decision_price,
                'current_price': current_price,
                'profit_loss': profit_loss,
                'is_success': is_success,
                'hours_elapsed': hours_elapsed
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def generate_reflection_note(
        self,
        decision: Dict,
        evaluation: Dict
    ) -> str:
        """
        Generate AI-powered reflection note

        Args:
            decision: Original decision record
            evaluation: Evaluation results

        Returns:
            Reflection note string
        """
        if not self.deep_agent:
            # Fallback to rule-based reflection
            return self._generate_simple_reflection(decision, evaluation)

        try:
            prompt = self._build_reflection_prompt(decision, evaluation)

            if self.ai_model == 'claude':
                response = self.deep_agent._call_claude(prompt)
            else:
                response = self.deep_agent._call_gpt(prompt)

            return response.strip()

        except Exception as e:
            print(f"Error generating AI reflection: {str(e)}")
            return self._generate_simple_reflection(decision, evaluation)

    def _build_reflection_prompt(
        self,
        decision: Dict,
        evaluation: Dict
    ) -> str:
        """Build prompt for AI reflection"""

        metadata = json.loads(decision['metadata']) if decision.get('metadata') else {}

        prompt = f"""You are analyzing a past trading decision to learn from it.

**Original Decision**:
- Ticker: {decision['ticker']}
- Action: {decision['action']}
- Price at decision: ${decision['price']:.2f}
- Confidence: {decision['confidence']}%
- Risk Level: {decision['risk_level']}
- Trigger Score: {decision['trigger_score']}/100

**Original Reasoning**:
{decision['reasoning']}

**Context at Decision Time**:
{json.dumps(metadata, indent=2)}

**Actual Outcome** ({evaluation['hours_elapsed']} hours later):
- Current Price: ${evaluation['current_price']:.2f}
- P/L: {evaluation['profit_loss']:+.2f}%
- Success: {'YES' if evaluation['is_success'] else 'NO'}

**Your Task**:
Analyze this decision critically in 2-3 sentences:
1. Was the reasoning sound given the available information?
2. What factors did we miss or misinterpret?
3. What should we do differently next time?

Be specific and actionable. Focus on improving future decisions.

Response:"""

        return prompt

    def _generate_simple_reflection(
        self,
        decision: Dict,
        evaluation: Dict
    ) -> str:
        """Generate simple rule-based reflection"""

        if evaluation['is_success']:
            return f"Decision was correct. {decision['action']} at ${decision['price']:.2f} resulted in {evaluation['profit_loss']:+.2f}% P/L. Original reasoning was sound."
        else:
            magnitude = abs(evaluation['profit_loss'])
            if magnitude > 5:
                severity = "significant"
            elif magnitude > 2:
                severity = "moderate"
            else:
                severity = "minor"

            return f"Decision was incorrect ({severity} loss of {evaluation['profit_loss']:+.2f}%). " \
                   f"Original confidence was {decision['confidence']}%. " \
                   f"Need to review: {decision['reasoning'][:100]}..."

    def run_reflection_cycle(
        self,
        min_hours_ago: int = 24,
        max_reflections: int = 10
    ) -> int:
        """
        Run reflection cycle on past unreflected decisions

        Args:
            min_hours_ago: Minimum hours since decision
            max_reflections: Maximum number of decisions to reflect on

        Returns:
            Number of reflections created
        """
        print(f"\n{'=' * 60}")
        print(f"REFLECTION CYCLE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 60}")

        # Get unreflected decisions
        decisions = self.db.get_decisions_without_reflection(min_hours_ago)

        if not decisions:
            print("✓ No decisions to reflect on")
            return 0

        decisions = decisions[:max_reflections]
        print(f"\nFound {len(decisions)} decisions to evaluate")

        reflections_created = 0

        for decision in decisions:
            print(f"\n  Evaluating {decision['ticker']} ({decision['action']})...")

            # Evaluate decision
            evaluation = self.evaluate_decision(
                decision,
                hours_elapsed=min_hours_ago
            )

            if not evaluation['success']:
                print(f"    ✗ {evaluation.get('error', 'Unknown error')}")
                continue

            # Generate reflection note
            print(f"    P/L: {evaluation['profit_loss']:+.2f}% ({'✓ Success' if evaluation['is_success'] else '✗ Failure'})")

            reflection_note = self.generate_reflection_note(decision, evaluation)

            # Save reflection
            reflection_id = self.db.log_reflection(
                decision_id=decision['id'],
                target_price=evaluation['current_price'],
                profit_loss=evaluation['profit_loss'],
                is_success=evaluation['is_success'],
                reflection_note=reflection_note
            )

            if reflection_id > 0:
                print(f"    ✓ Reflection saved (ID: {reflection_id})")
                print(f"    Note: {reflection_note[:80]}...")
                reflections_created += 1
            else:
                print(f"    ✗ Failed to save reflection")

        print(f"\n{'=' * 60}")
        print(f"✓ Created {reflections_created} reflections")

        # Print summary statistics
        stats = self.db.get_success_rate(days=30)
        print(f"\n📊 30-Day Statistics:")
        print(f"  Total Decisions: {stats['total_decisions']}")
        print(f"  Success Rate: {stats['success_rate']:.1f}%")
        print(f"  Avg P/L: {stats['avg_pnl']:+.2f}%")
        print(f"{'=' * 60}\n")

        return reflections_created

    def get_learning_summary(self, limit: int = 5) -> str:
        """
        Get summary of recent learnings for context injection

        Args:
            limit: Number of recent reflections to include

        Returns:
            Summary string for agent prompt
        """
        reflections = self.db.get_recent_reflections(limit=limit)

        if not reflections:
            return "No prior reflections available."

        summary = "📚 Recent Learnings from Past Decisions:\n\n"

        for i, r in enumerate(reflections, 1):
            success_marker = "✓" if r['is_success'] else "✗"
            summary += f"{i}. {success_marker} {r['ticker']} ({r['action']}) - {r['profit_loss']:+.1f}%\n"
            summary += f"   Original: {r['decision_reasoning'][:60]}...\n"
            summary += f"   Learning: {r['reflection_note'][:100]}...\n\n"

        # Add success rate
        stats = self.db.get_success_rate(days=7)
        summary += f"Recent Performance (7 days):\n"
        summary += f"  Success Rate: {stats['success_rate']:.1f}%\n"
        summary += f"  Avg P/L: {stats['avg_pnl']:+.2f}%\n"

        return summary


def test_reflection():
    """Test reflection engine"""
    print("Testing Reflection Engine...")

    # Initialize
    db = TradingDatabase('test_nanoquant.db')
    engine = ReflectionEngine(db_path='test_nanoquant.db', ai_model='claude')

    # Log some test decisions
    print("\n1. Creating test decisions...")

    decision_id_1 = db.log_decision(
        ticker='AAPL',
        action='BUY',
        price=150.0,
        amount=5.0,
        confidence=85.0,
        risk_level='LOW',
        reasoning='Strong earnings beat with positive guidance',
        trigger_score=75,
        metadata={'news': 'earnings beat', 'volume_ratio': 1.8}
    )
    print(f"   Decision 1 logged (ID: {decision_id_1})")

    # Manually set timestamp to 25 hours ago for testing
    import sqlite3
    conn = sqlite3.connect('test_nanoquant.db')
    conn.execute('''
        UPDATE decisions
        SET timestamp = datetime('now', '-25 hours')
        WHERE id = ?
    ''', (decision_id_1,))
    conn.commit()
    conn.close()

    # Run reflection cycle
    print("\n2. Running reflection cycle...")
    count = engine.run_reflection_cycle(min_hours_ago=24)

    # Get learning summary
    print("\n3. Getting learning summary...")
    summary = engine.get_learning_summary(limit=3)
    print(summary)


if __name__ == '__main__':
    test_reflection()
