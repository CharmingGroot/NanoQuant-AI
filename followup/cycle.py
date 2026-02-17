"""
followup/cycle.py - 판단 사후 추적 실행 (가격 조회, pnl, is_success, LLM 학습 메모)
"""

import json
import logging
from typing import Dict

from core import TradingDatabase, DataFetcher, DeepAgent

logger = logging.getLogger('NanoQuant')


def get_is_success(action: str, pnl_pct: float) -> bool:
    """BUY: pnl>0, SELL: pnl<0, HOLD: pnl<0"""
    if action == 'BUY':
        return pnl_pct > 0
    if action in ('SELL', 'HOLD'):
        return pnl_pct < 0
    return False


def _generate_reflection_note(
    decision: Dict,
    followup_price: float,
    pnl_pct: float,
    is_success: bool,
    deep_agent: DeepAgent = None,
    ai_model: str = 'claude'
) -> str:
    """LLM 또는 룰 기반으로 학습 메모 생성"""
    if deep_agent:
        try:
            prompt = _build_reflection_prompt(decision, followup_price, pnl_pct, is_success)
            if ai_model == 'claude':
                return deep_agent._call_claude(prompt).strip()
            return deep_agent._call_gpt(prompt).strip()
        except Exception as e:
            logger.warning(f"  [Reflection] LLM 실패, 룰 기반 사용: {e}")
    return _simple_reflection(decision, pnl_pct, is_success)


def _build_reflection_prompt(
    decision: Dict,
    followup_price: float,
    pnl_pct: float,
    is_success: bool
) -> str:
    meta = {}
    try:
        meta = json.loads(decision['metadata']) if decision.get('metadata') else {}
    except (json.JSONDecodeError, TypeError):
        pass

    return f"""You are analyzing a past trading decision to learn from it.

**Original Decision**:
- Ticker: {decision['ticker']}
- Action: {decision['action']}
- Price at decision: ${float(decision['price']):.2f}
- Confidence: {decision['confidence']}%
- Risk Level: {decision['risk_level']}
- Trigger Score: {decision['trigger_score']}/100

**Original Reasoning**:
{decision.get('reasoning', '')}

**Context at Decision Time**:
{json.dumps(meta, indent=2, ensure_ascii=False)}

**Actual Outcome** (24h later):
- Current Price: ${followup_price:.2f}
- P/L: {pnl_pct:+.2f}%
- Success: {'YES' if is_success else 'NO'}

**Your Task**:
Analyze this decision critically in 2-3 sentences (Korean):
1. Was the reasoning sound given the available information?
2. What factors did we miss or misinterpret?
3. What should we do differently next time?

Be specific and actionable. Respond in Korean.

Response:"""


def _simple_reflection(decision: Dict, pnl_pct: float, is_success: bool) -> str:
    if is_success:
        return f"판단 적중. {decision['action']} @ ${decision['price']:.2f} → {pnl_pct:+.2f}% P/L. 원래 근거 타당."
    mag = abs(pnl_pct)
    sev = "큰" if mag > 5 else ("중간" if mag > 2 else "작은")
    return f"판단 오류 ({sev} 손실 {pnl_pct:+.2f}%). 확신도 {decision['confidence']}%. 검토 필요: {(decision.get('reasoning') or '')[:80]}..."


def run_decision_followup_cycle(
    db_path: str = 'nanoquant_v1.db',
    min_hours_ago: int = 24,
    max_followups: int = 30,
    ai_model: str = 'claude',
    use_llm_reflection: bool = True
) -> int:
    """
    모든 판단(BUY/SELL/HOLD)의 사후 추적 + LLM 학습 메모
    """
    db = TradingDatabase(db_path)
    fetcher = DataFetcher()
    deep_agent = None
    if use_llm_reflection:
        try:
            deep_agent = DeepAgent(model=ai_model, max_position_size=5.0)
        except Exception as e:
            logger.warning(f"[DecisionFollowup] LLM 초기화 실패, 룰 기반만 사용: {e}")

    decisions = db.get_decisions_for_followup(min_hours_ago=min_hours_ago, limit=max_followups)

    if not decisions:
        logger.info("[DecisionFollowup] 처리할 후속 대상 없음")
        return 0

    processed = 0
    for d in decisions:
        try:
            ticker = d['ticker']
            action = d.get('action', 'HOLD')
            decision_price = float(d['price'] or 0)
            decision_id = d['id']

            if decision_price <= 0:
                continue

            current_price = fetcher.get_current_price(ticker)
            if current_price is None:
                logger.warning(f"  [DecisionFollowup] {ticker} 현재가 조회 실패")
                continue

            pnl_pct = (current_price - decision_price) / decision_price * 100
            is_success = get_is_success(action, pnl_pct)
            reflection_note = _generate_reflection_note(
                d, current_price, pnl_pct, is_success,
                deep_agent=deep_agent, ai_model=ai_model
            )

            db.log_decision_followup(
                decision_id=decision_id,
                followup_price=current_price,
                pnl_pct=pnl_pct,
                is_success=is_success,
                reflection_note=reflection_note
            )

            label = "올바름" if is_success else "틀림"
            logger.info(
                f"  [DecisionFollowup] {action} {ticker} #{decision_id}: "
                f"${decision_price:.2f} → ${current_price:.2f} ({pnl_pct:+.2f}%) [{label}]"
            )
            processed += 1

        except Exception as e:
            logger.exception(f"  [DecisionFollowup] {d.get('ticker', '?')} 처리 실패: {e}")

    if processed > 0:
        stats = db.get_success_rate(days=30)
        logger.info(f"[DecisionFollowup] 완료: {processed}건 | 30일 성공률: {stats['success_rate']:.1f}%")
    return processed
