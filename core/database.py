"""
core/database.py - SQLite database for decision logging and reflection
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from contextlib import contextmanager

import pandas as pd


class TradingDatabase:
    """SQLite database manager for trading decisions and reflections"""

    def __init__(self, db_path: str = 'nanoquant_v1.db'):
        self.db_path = db_path
        self._init_tables()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_tables(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
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
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS decision_followups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    decision_id INTEGER NOT NULL,
                    followup_price REAL NOT NULL,
                    followup_at TEXT NOT NULL,
                    pnl_pct REAL NOT NULL,
                    is_success INTEGER,
                    reflection_note TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (decision_id) REFERENCES decisions (id),
                    UNIQUE (decision_id)
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_decisions_ticker ON decisions (ticker)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_decisions_timestamp ON decisions (timestamp)')
            cursor.execute("PRAGMA table_info(decisions)")
            cols = [row[1] for row in cursor.fetchall()]
            if 'cycle_id' not in cols:
                try:
                    cursor.execute("ALTER TABLE decisions ADD COLUMN cycle_id TEXT")
                except Exception:
                    pass
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_decision_followups_decision ON decision_followups (decision_id)')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_bars (
                    ticker TEXT NOT NULL,
                    date TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (ticker, date)
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_bars_ticker_date ON daily_bars (ticker, date)')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS forecast_cache (
                    ticker TEXT NOT NULL,
                    model TEXT NOT NULL,
                    data_hash TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (ticker, model)
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_forecast_cache_ticker_model ON forecast_cache (ticker, model)')
            cursor.execute("PRAGMA table_info(decision_followups)")
            cols = [row[1] for row in cursor.fetchall()]
            if 'is_success' not in cols:
                cursor.execute("ALTER TABLE decision_followups ADD COLUMN is_success INTEGER")
            if 'reflection_note' not in cols:
                cursor.execute("ALTER TABLE decision_followups ADD COLUMN reflection_note TEXT")
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hold_followups'")
            if cursor.fetchone():
                cursor.execute('''
                    INSERT OR IGNORE INTO decision_followups (decision_id, followup_price, followup_at, pnl_pct)
                    SELECT decision_id, followup_price, followup_at, pnl_pct FROM hold_followups
                    WHERE decision_id NOT IN (SELECT decision_id FROM decision_followups)
                ''')

    def log_decision(self, ticker: str, action: str, price: float, amount: float, confidence: float,
                     risk_level: str, reasoning: str, trigger_score: int, metadata: Dict = None,
                     cycle_id: Optional[str] = None) -> int:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO decisions (timestamp, ticker, action, price, amount, confidence,
                     risk_level, reasoning, trigger_score, metadata, cycle_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (datetime.now().isoformat(), ticker, action, price, amount, confidence,
                      risk_level, reasoning, trigger_score, json.dumps(metadata) if metadata else None, cycle_id))
                return cursor.lastrowid
        except Exception as e:
            print(f"Error logging decision: {str(e)}")
            return -1

    def count_decisions(self, ticker: Optional[str] = None, action: Optional[str] = None) -> int:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = 'SELECT COUNT(*) FROM decisions WHERE 1=1'
                params = []
                if ticker:
                    query += ' AND ticker = ?'
                    params.append(ticker)
                if action:
                    query += ' AND action = ?'
                    params.append(action)
                cursor.execute(query, params)
                return int(cursor.fetchone()[0])
        except Exception:
            return 0

    def get_decisions(self, ticker: Optional[str] = None, action: Optional[str] = None,
                      limit: int = 100, offset: int = 0) -> List[Dict]:
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
                query += ' ORDER BY timestamp DESC LIMIT ? OFFSET ?'
                params.extend([limit, offset])
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error fetching decisions: {str(e)}")
            return []

    def get_decisions_without_reflection(self, min_hours_ago: int = 24) -> List[Dict]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT d.* FROM decisions d
                    LEFT JOIN reflections r ON d.id = r.decision_id
                    WHERE r.id IS NULL AND d.action IN ('BUY', 'SELL')
                    AND datetime(d.timestamp) <= datetime('now', '-' || ? || ' hours')
                    ORDER BY d.timestamp ASC
                ''', (min_hours_ago,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error fetching unreflected decisions: {str(e)}")
            return []

    def get_decisions_for_followup(self, min_hours_ago: int = 24, limit: int = 50) -> List[Dict]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT d.* FROM decisions d
                    LEFT JOIN decision_followups f ON d.id = f.decision_id
                    WHERE f.id IS NULL AND d.price > 0
                    AND datetime(d.timestamp) <= datetime('now', '-' || ? || ' hours')
                    ORDER BY d.timestamp ASC LIMIT ?
                ''', (min_hours_ago, limit))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error fetching decisions for followup: {str(e)}")
            return []

    def log_decision_followup(self, decision_id: int, followup_price: float, pnl_pct: float,
                              is_success: bool = None, reflection_note: str = None) -> int:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO decision_followups (decision_id, followup_price, followup_at, pnl_pct, is_success, reflection_note)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (decision_id, followup_price, datetime.now().isoformat(), pnl_pct,
                      1 if is_success else 0 if is_success is False else None, reflection_note))
                return cursor.lastrowid
        except Exception as e:
            print(f"Error logging decision followup: {str(e)}")
            return -1

    def get_decision_followups(self, limit: int = 100) -> List[Dict]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT d.id, d.ticker, d.action, d.timestamp, d.price AS decision_price,
                        d.reasoning, d.confidence, d.risk_level, d.trigger_score, d.metadata,
                        f.followup_price, f.followup_at, f.pnl_pct, f.is_success, f.reflection_note
                    FROM decisions d JOIN decision_followups f ON d.id = f.decision_id
                    ORDER BY d.timestamp DESC LIMIT ?
                ''', (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error fetching decision followups: {str(e)}")
            return []

    def log_reflection(self, decision_id: int, target_price: float, profit_loss: float,
                       is_success: bool, reflection_note: str) -> int:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO reflections (decision_id, eval_timestamp, target_price, profit_loss, is_success, reflection_note)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (decision_id, datetime.now().isoformat(), target_price, profit_loss, 1 if is_success else 0, reflection_note))
                return cursor.lastrowid
        except Exception as e:
            print(f"Error logging reflection: {str(e)}")
            return -1

    def get_recent_reflections(self, limit: int = 10) -> List[Dict]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT d.ticker, d.action, d.price AS decision_price, d.reasoning AS decision_reasoning,
                        d.confidence, f.followup_price AS target_price, f.pnl_pct AS profit_loss,
                        f.is_success, f.reflection_note, f.followup_at AS eval_timestamp
                    FROM decision_followups f JOIN decisions d ON f.decision_id = d.id
                    ORDER BY f.followup_at DESC LIMIT ?
                ''', (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error fetching reflections: {str(e)}")
            return []

    def get_learning_summary(self, limit: int = 5) -> str:
        rows = self.get_recent_reflections(limit=limit)
        if not rows:
            return "No prior reflections available."
        summary = "📚 Recent Learnings from Past Decisions:\n\n"
        for i, r in enumerate(rows, 1):
            success_marker = "✓" if r.get('is_success') else "✗"
            summary += f"{i}. {success_marker} {r['ticker']} ({r['action']}) - {r.get('profit_loss', 0):+.1f}%\n"
            summary += f"   Original: {(r.get('decision_reasoning') or '')[:60]}...\n"
            summary += f"   Learning: {(r.get('reflection_note') or '')[:100]}...\n\n"
        stats = self.get_success_rate(days=7)
        summary += f"Recent Performance (7 days):\n  Success Rate: {stats['success_rate']:.1f}%\n  Avg P/L: {stats['avg_pnl']:+.2f}%\n"
        return summary

    def get_success_rate(self, ticker: Optional[str] = None, days: int = 30) -> Dict[str, float]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = '''
                    SELECT COUNT(*) as total, SUM(f.is_success) as successes, AVG(f.pnl_pct) as avg_pnl
                    FROM decision_followups f JOIN decisions d ON f.decision_id = d.id
                    WHERE datetime(f.followup_at) >= datetime('now', '-' || ? || ' days')
                '''
                params = [days]
                if ticker:
                    query += ' AND d.ticker = ?'
                    params.append(ticker)
                cursor.execute(query, params)
                row = cursor.fetchone()
                if row and row['total'] > 0:
                    return {'total_decisions': row['total'], 'successes': row['successes'] or 0,
                            'success_rate': (row['successes'] or 0) / row['total'] * 100, 'avg_pnl': row['avg_pnl'] or 0}
                return {'total_decisions': 0, 'successes': 0, 'success_rate': 0, 'avg_pnl': 0}
        except Exception as e:
            print(f"Error calculating success rate: {str(e)}")
            return {'total_decisions': 0, 'successes': 0, 'success_rate': 0, 'avg_pnl': 0}

    def save_daily_bars(self, ticker: str, df: pd.DataFrame) -> int:
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            return 0
        ticker = str(ticker).upper()
        date_col = 'timestamp' if 'timestamp' in df.columns else ('date' if 'date' in df.columns else df.columns[0])
        open_col, high_col, low_col = 'open' if 'open' in df.columns else 'Open', 'high' if 'high' in df.columns else 'High', 'low' if 'low' in df.columns else 'Low'
        close_col, vol_col = 'close' if 'close' in df.columns else 'Close', 'volume' if 'volume' in df.columns else 'Volume'
        updated = datetime.now().isoformat()
        count = 0
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                for _, row in df.iterrows():
                    dt = row.get(date_col)
                    if pd.isna(dt):
                        continue
                    d = pd.to_datetime(dt).strftime('%Y-%m-%d')
                    o, h, lo, c, v = float(row.get(open_col, 0) or 0), float(row.get(high_col, 0) or 0), float(row.get(low_col, 0) or 0), float(row.get(close_col, 0) or 0), float(row.get(vol_col, 0) or 0)
                    cursor.execute('INSERT OR REPLACE INTO daily_bars (ticker, date, open, high, low, close, volume, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (ticker, d, o, h, lo, c, v, updated))
                    count += 1
        except Exception as e:
            print(f"Error saving daily_bars for {ticker}: {str(e)}")
        return count

    def get_daily_bars(self, ticker: str, days: int = 252) -> Optional[pd.DataFrame]:
        ticker = str(ticker).upper()
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT date AS timestamp, open, high, low, close, volume FROM daily_bars WHERE ticker = ? ORDER BY date DESC LIMIT ?', (ticker, days))
                rows = cursor.fetchall()
        except Exception as e:
            print(f"Error reading daily_bars for {ticker}: {str(e)}")
            return None
        if not rows:
            return None
        df = pd.DataFrame(rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        return df.iloc[::-1].reset_index(drop=True)

    def save_forecast_cache(self, ticker: str, model: str, data_hash: str, payload: dict) -> bool:
        ticker = str(ticker).upper()
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT OR REPLACE INTO forecast_cache (ticker, model, data_hash, payload, created_at) VALUES (?, ?, ?, ?, ?)', (ticker, model, data_hash, json.dumps(payload), datetime.now().isoformat()))
            return True
        except Exception as e:
            print(f"Error saving forecast_cache for {ticker}/{model}: {str(e)}")
            return False

    def get_forecast_cache(self, ticker: str, model: str, data_hash: str) -> Optional[dict]:
        ticker = str(ticker).upper()
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT payload FROM forecast_cache WHERE ticker = ? AND model = ? AND data_hash = ?', (ticker, model, data_hash))
                row = cursor.fetchone()
        except Exception as e:
            print(f"Error reading forecast_cache for {ticker}/{model}: {str(e)}")
            return None
        if not row:
            return None
        try:
            return json.loads(row['payload'])
        except (json.JSONDecodeError, TypeError):
            return None
