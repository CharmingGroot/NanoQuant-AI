"""
reflection.py - (Deprecated) 리플렉션 로직은 followup/로 이동됨

사후 추적 + LLM 학습 메모는 followup.run_decision_followup_cycle()에서 처리.
학습 요약은 database.TradingDatabase.get_learning_summary() 사용.
"""

# 하위 호환: ReflectionEngine을 사용하는 외부 스크립트용 스텁
from followup import run_decision_followup_cycle
from core import TradingDatabase


class ReflectionEngine:
    """Deprecated. Use followup.run_decision_followup_cycle + db.get_learning_summary"""

    def __init__(self, db_path: str = 'nanoquant_v1.db', ai_model: str = 'claude'):
        import warnings
        warnings.warn(
            "ReflectionEngine is deprecated. Use followup.run_decision_followup_cycle() and db.get_learning_summary()",
            DeprecationWarning,
            stacklevel=2
        )
        self.db = TradingDatabase(db_path)
        self.ai_model = ai_model

    def get_learning_summary(self, limit: int = 5) -> str:
        return self.db.get_learning_summary(limit=limit)

    def run_reflection_cycle(self, min_hours_ago: int = 24, max_reflections: int = 10) -> int:
        return run_decision_followup_cycle(
            db_path=self.db.db_path,
            min_hours_ago=min_hours_ago,
            max_followups=max_reflections,
            ai_model=self.ai_model
        )
