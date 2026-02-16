"""
run_reflection.py - 리플렉션(판단 사후 추적 + LLM 학습메모) 임의 실행

사용법:
  python run_reflection.py
  python run_reflection.py --hours 24 --limit 50
  python run_reflection.py --hours 1   # 테스트용 1시간 경과만
"""

import argparse
import logging
import os

from dotenv import load_dotenv

from missed_profit import run_decision_followup_cycle

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('Reflection')


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description='리플렉션 실행 (판단 사후 추적 + LLM 학습메모)')
    parser.add_argument('--hours', type=int, default=24, help='최소 경과 시간(시간). 기본 24')
    parser.add_argument('--limit', type=int, default=30, help='한 번에 처리할 최대 건수. 기본 30')
    parser.add_argument('--db', type=str, default=None, help='DB 경로. 기본: 프로젝트/nanoquant_v1.db')
    parser.add_argument('--no-llm', action='store_true', help='LLM 비활성화, 룰 기반만 사용')
    parser.add_argument('--model', type=str, default='claude', choices=['claude', 'gpt'], help='AI 모델')
    args = parser.parse_args()

    db_path = args.db or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nanoquant_v1.db')

    logger.info("=" * 60)
    logger.info("리플렉션 실행 (판단 사후 추적 + LLM 학습메모)")
    logger.info(f"  DB: {db_path}")
    logger.info(f"  최소 경과: {args.hours}시간")
    logger.info(f"  최대 건수: {args.limit}")
    logger.info(f"  LLM: {'OFF' if args.no_llm else f'ON ({args.model})'}")
    logger.info("=" * 60)

    n = run_decision_followup_cycle(
        db_path=db_path,
        min_hours_ago=args.hours,
        max_followups=args.limit,
        ai_model=args.model,
        use_llm_reflection=not args.no_llm
    )

    logger.info(f"\n완료: {n}건 처리")


if __name__ == '__main__':
    main()
