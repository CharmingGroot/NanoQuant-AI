/**
 * SQLite — KG 영속성 + 백테스트 실행 이력 (docs/menu/kg/06, execution-plan C-2)
 */
import Database from "better-sqlite3";
import path from "path";
import fs from "fs";

let db: Database.Database | null = null;

const DEFAULT_DB_PATH = path.join(process.cwd(), "data", "nanoquant.db");

export function initDb(dbPath?: string): void {
  if (db) return;
  const target = dbPath ?? DEFAULT_DB_PATH;
  const dir = path.dirname(target);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  db = new Database(target);
  db.pragma("journal_mode = WAL");

  db.exec(`
    CREATE TABLE IF NOT EXISTS kg_nodes (
      id TEXT PRIMARY KEY,
      type TEXT NOT NULL,
      data TEXT NOT NULL DEFAULT '{}',
      created_at INTEGER NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_kg_nodes_type ON kg_nodes(type);
    CREATE INDEX IF NOT EXISTS idx_kg_nodes_created ON kg_nodes(created_at);

    CREATE TABLE IF NOT EXISTS kg_edges (
      from_id TEXT NOT NULL,
      to_id TEXT NOT NULL,
      type TEXT NOT NULL,
      created_at INTEGER NOT NULL,
      PRIMARY KEY (from_id, to_id, type),
      FOREIGN KEY (from_id) REFERENCES kg_nodes(id),
      FOREIGN KEY (to_id) REFERENCES kg_nodes(id)
    );

    CREATE TABLE IF NOT EXISTS backtest_runs (
      id TEXT PRIMARY KEY,
      start_date TEXT NOT NULL,
      end_date TEXT NOT NULL,
      symbols TEXT NOT NULL,
      strategy_type TEXT NOT NULL,
      strategy_params TEXT,
      total_return_pct REAL,
      annualized_return_pct REAL,
      max_drawdown_pct REAL,
      trade_count INTEGER,
      win_rate REAL,
      result_json TEXT,
      created_at INTEGER NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_backtest_runs_created ON backtest_runs(created_at DESC);
  `);
}

export function closeDb(): void {
  if (db) {
    db.close();
    db = null;
  }
}

function getDb(): Database.Database {
  if (!db) throw new Error("DB not initialized. Call initDb() first.");
  return db;
}

// --- KG ---

export interface KgNodeRow {
  id: string;
  type: string;
  data: string;
  created_at: number;
}

export interface KgEdgeRow {
  from_id: string;
  to_id: string;
  type: string;
  created_at: number;
}

export function loadKgNodes(): KgNodeRow[] {
  try {
    const d = getDb();
    const rows = d.prepare("SELECT id, type, data, created_at FROM kg_nodes").all() as KgNodeRow[];
    return rows;
  } catch {
    return [];
  }
}

export function loadKgEdges(): KgEdgeRow[] {
  try {
    const d = getDb();
    const rows = d.prepare("SELECT from_id, to_id, type, created_at FROM kg_edges").all() as KgEdgeRow[];
    return rows;
  } catch {
    return [];
  }
}

export function insertKgNode(id: string, type: string, data: Record<string, unknown>): void {
  try {
    getDb()
      .prepare("INSERT OR REPLACE INTO kg_nodes (id, type, data, created_at) VALUES (?, ?, ?, ?)")
      .run(id, type, JSON.stringify(data ?? {}), Math.floor(Date.now() / 1000));
  } catch (e) {
    console.warn("KG insert node failed:", e);
  }
}

export function insertKgEdge(fromId: string, toId: string, edgeType: string): void {
  try {
    getDb()
      .prepare("INSERT OR IGNORE INTO kg_edges (from_id, to_id, type, created_at) VALUES (?, ?, ?, ?)")
      .run(fromId, toId, edgeType, Math.floor(Date.now() / 1000));
  } catch (e) {
    console.warn("KG insert edge failed:", e);
  }
}

// --- Backtest runs ---

export interface BacktestRunRow {
  id: string;
  start_date: string;
  end_date: string;
  symbols: string;
  strategy_type: string;
  strategy_params: string | null;
  total_return_pct: number | null;
  annualized_return_pct: number | null;
  max_drawdown_pct: number | null;
  trade_count: number | null;
  win_rate: number | null;
  result_json: string | null;
  created_at: number;
}

export function insertBacktestRun(
  id: string,
  params: { start_date: string; end_date: string; symbols: string[]; strategy_type: string; strategy_params?: Record<string, unknown> },
  result: {
    total_return_pct?: number;
    annualized_return_pct?: number;
    max_drawdown_pct?: number;
    trade_count?: number;
    win_rate?: number;
    equity_curve?: number[];
    trades?: unknown[];
  }
): void {
  try {
    const d = getDb();
    d.prepare(
      `INSERT INTO backtest_runs (id, start_date, end_date, symbols, strategy_type, strategy_params, total_return_pct, annualized_return_pct, max_drawdown_pct, trade_count, win_rate, result_json, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
    ).run(
      id,
      params.start_date,
      params.end_date,
      JSON.stringify(params.symbols),
      params.strategy_type,
      params.strategy_params ? JSON.stringify(params.strategy_params) : null,
      result.total_return_pct ?? null,
      result.annualized_return_pct ?? null,
      result.max_drawdown_pct ?? null,
      result.trade_count ?? null,
      result.win_rate ?? null,
      JSON.stringify({ equity_curve: result.equity_curve, trades: result.trades }),
      Math.floor(Date.now() / 1000)
    );
  } catch (e) {
    console.warn("Backtest run insert failed:", e);
  }
}

export function getBacktestRuns(limit = 20): BacktestRunRow[] {
  if (!db) return [];
  try {
    const d = getDb();
    const rows = d
      .prepare(
        "SELECT id, start_date, end_date, symbols, strategy_type, strategy_params, total_return_pct, annualized_return_pct, max_drawdown_pct, trade_count, win_rate, result_json, created_at FROM backtest_runs ORDER BY created_at DESC LIMIT ?"
      )
      .all(limit) as BacktestRunRow[];
    return rows;
  } catch {
    return [];
  }
}

export function getBacktestRunById(id: string): BacktestRunRow | null {
  if (!db) return null;
  try {
    const d = getDb();
    const row = d
      .prepare(
        "SELECT id, start_date, end_date, symbols, strategy_type, strategy_params, total_return_pct, annualized_return_pct, max_drawdown_pct, trade_count, win_rate, result_json, created_at FROM backtest_runs WHERE id = ?"
      )
      .get(id) as BacktestRunRow | undefined;
    return row ?? null;
  } catch {
    return null;
  }
}

export function isDbEnabled(): boolean {
  return db != null;
}
