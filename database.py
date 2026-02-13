"""
database.py - SQLite database for decision logging and reflection
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from contextlib import contextmanager


class TradingDatabase:
    """SQLite database manager for trading decisions and reflections"""

    def __init__(self, db_path: str = 'nanoquant_v1.db'):
        """
        Initialize database connection

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_tables()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_tables(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # decisions 테이블 (판단 기록)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    action TEXT NOT NULL,
                    price REAL NOT NULL,
                    amount REAL NOT NULL,
                    confidence REAL NOT NULL,
                    risk_level TEXT,
                    reasoning TEXT,
                    trigger_score INTEGER,
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # reflections 테이블 (사후 성찰)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reflections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    decision_id INTEGER NOT NULL,
                    eval_timestamp TEXT NOT NULL,
                    target_price REAL,
                    profit_loss REAL,
                    is_success INTEGER,
                    reflection_note TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (decision_id) REFERENCES decisions (id)
                )
            ''')

            # Index for faster queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_decisions_ticker
                ON decisions (ticker)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_decisions_timestamp
                ON decisions (timestamp)
            ''')

    def log_decision(
        self,
        ticker: str,
        action: str,
        price: float,
        amount: float,
        confidence: float,
        risk_level: str,
        reasoning: str,
        trigger_score: int,
        metadata: Dict = None
    ) -> int:
        """
        Log a trading decision

        Args:
            ticker: Stock ticker
            action: BUY/SELL/HOLD
            price: Current price
            amount: Dollar amount or percentage
            confidence: Confidence score (0-100)
            risk_level: LOW/MEDIUM/HIGH
            reasoning: AI's reasoning
            trigger_score: Total trigger score
            metadata: Additional data (news, volume, etc.)

        Returns:
            Decision ID
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT INTO decisions
                    (timestamp, ticker, action, price, amount, confidence,
                     risk_level, reasoning, trigger_score, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now().isoformat(),
                    ticker,
                    action,
                    price,
                    amount,
                    confidence,
                    risk_level,
                    reasoning,
                    trigger_score,
                    json.dumps(metadata) if metadata else None
                ))

                return cursor.lastrowid

        except Exception as e:
            print(f"Error logging decision: {str(e)}")
            return -1

    def get_decisions(
        self,
        ticker: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get decisions from database

        Args:
            ticker: Filter by ticker (optional)
            action: Filter by action (optional)
            limit: Maximum number of results

        Returns:
            List of decision records
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                query = 'SELECT * FROM decisions WHERE 1=1'
                params = []

                if ticker:
                    query += ' AND ticker = ?'
                    params.append(ticker)

                if action:
                    query += ' AND action = ?'
                    params.append(action)

                query += ' ORDER BY timestamp DESC LIMIT ?'
                params.append(limit)

                cursor.execute(query, params)

                rows = cursor.fetchall()
                return [dict(row) for row in rows]

        except Exception as e:
            print(f"Error fetching decisions: {str(e)}")
            return []

    def get_decisions_without_reflection(
        self,
        min_hours_ago: int = 24
    ) -> List[Dict]:
        """
        Get decisions that haven't been reflected on yet

        Args:
            min_hours_ago: Minimum hours since decision

        Returns:
            List of unreflected decisions
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT d.* FROM decisions d
                    LEFT JOIN reflections r ON d.id = r.decision_id
                    WHERE r.id IS NULL
                    AND d.action IN ('BUY', 'SELL')
                    AND datetime(d.timestamp) <= datetime('now', '-' || ? || ' hours')
                    ORDER BY d.timestamp ASC
                ''', (min_hours_ago,))

                rows = cursor.fetchall()
                return [dict(row) for row in rows]

        except Exception as e:
            print(f"Error fetching unreflected decisions: {str(e)}")
            return []

    def log_reflection(
        self,
        decision_id: int,
        target_price: float,
        profit_loss: float,
        is_success: bool,
        reflection_note: str
    ) -> int:
        """
        Log a reflection on a past decision

        Args:
            decision_id: ID of the decision being reflected on
            target_price: Actual price after time period
            profit_loss: Profit/loss percentage
            is_success: Whether the decision was correct
            reflection_note: AI's analysis of the outcome

        Returns:
            Reflection ID
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT INTO reflections
                    (decision_id, eval_timestamp, target_price, profit_loss,
                     is_success, reflection_note)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    decision_id,
                    datetime.now().isoformat(),
                    target_price,
                    profit_loss,
                    1 if is_success else 0,
                    reflection_note
                ))

                return cursor.lastrowid

        except Exception as e:
            print(f"Error logging reflection: {str(e)}")
            return -1

    def get_recent_reflections(self, limit: int = 10) -> List[Dict]:
        """
        Get recent reflections with decision details

        Args:
            limit: Maximum number of results

        Returns:
            List of reflections with decision context
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT
                        d.ticker,
                        d.action,
                        d.price AS decision_price,
                        d.reasoning AS decision_reasoning,
                        d.confidence,
                        r.target_price,
                        r.profit_loss,
                        r.is_success,
                        r.reflection_note,
                        r.eval_timestamp
                    FROM reflections r
                    JOIN decisions d ON r.decision_id = d.id
                    ORDER BY r.eval_timestamp DESC
                    LIMIT ?
                ''', (limit,))

                rows = cursor.fetchall()
                return [dict(row) for row in rows]

        except Exception as e:
            print(f"Error fetching reflections: {str(e)}")
            return []

    def get_success_rate(
        self,
        ticker: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, float]:
        """
        Calculate success rate of decisions

        Args:
            ticker: Filter by ticker (optional)
            days: Number of days to look back

        Returns:
            Dict with success metrics
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                query = '''
                    SELECT
                        COUNT(*) as total,
                        SUM(r.is_success) as successes,
                        AVG(r.profit_loss) as avg_pnl
                    FROM reflections r
                    JOIN decisions d ON r.decision_id = d.id
                    WHERE datetime(r.eval_timestamp) >= datetime('now', '-' || ? || ' days')
                '''
                params = [days]

                if ticker:
                    query += ' AND d.ticker = ?'
                    params.append(ticker)

                cursor.execute(query, params)
                row = cursor.fetchone()

                if row and row['total'] > 0:
                    return {
                        'total_decisions': row['total'],
                        'successes': row['successes'] or 0,
                        'success_rate': (row['successes'] or 0) / row['total'] * 100,
                        'avg_pnl': row['avg_pnl'] or 0
                    }
                else:
                    return {
                        'total_decisions': 0,
                        'successes': 0,
                        'success_rate': 0,
                        'avg_pnl': 0
                    }

        except Exception as e:
            print(f"Error calculating success rate: {str(e)}")
            return {
                'total_decisions': 0,
                'successes': 0,
                'success_rate': 0,
                'avg_pnl': 0
            }


def test_database():
    """Test database functionality"""
    db = TradingDatabase('test_nanoquant.db')

    print("Testing database...")

    # Test 1: Log a decision
    print("\n1. Logging decision...")
    decision_id = db.log_decision(
        ticker='TSLA',
        action='BUY',
        price=250.0,
        amount=5.0,
        confidence=85.0,
        risk_level='MEDIUM',
        reasoning='Strong momentum with positive news catalyst',
        trigger_score=80,
        metadata={'news': 'Earnings beat', 'volume_ratio': 2.5}
    )
    print(f"   Decision logged with ID: {decision_id}")

    # Test 2: Get decisions
    print("\n2. Fetching decisions...")
    decisions = db.get_decisions(limit=5)
    print(f"   Found {len(decisions)} decisions")

    # Test 3: Log reflection
    print("\n3. Logging reflection...")
    reflection_id = db.log_reflection(
        decision_id=decision_id,
        target_price=255.0,
        profit_loss=2.0,
        is_success=True,
        reflection_note='Decision was correct. Price increased as predicted.'
    )
    print(f"   Reflection logged with ID: {reflection_id}")

    # Test 4: Get success rate
    print("\n4. Calculating success rate...")
    stats = db.get_success_rate(days=30)
    print(f"   Success rate: {stats['success_rate']:.1f}%")
    print(f"   Avg P/L: {stats['avg_pnl']:+.2f}%")

    print("\n✓ Database tests completed")


if __name__ == '__main__':
    test_database()
