/**
 * 과거 일봉 조회 — 백테스트용
 * 1단계: 스텁 데이터(심볼·날짜 기반 결정론적 시계열). 추후 yahoo-finance2 등 연동.
 */
export interface OHLCVRow {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

/** 날짜 구간 내 영업일 생성 (단순: 주말 제외) */
function businessDaysBetween(start: Date, end: Date): string[] {
  const out: string[] = [];
  const d = new Date(start);
  d.setHours(0, 0, 0, 0);
  const e = new Date(end);
  e.setHours(23, 59, 59, 999);
  while (d <= e) {
    const day = d.getDay();
    if (day !== 0 && day !== 6) out.push(d.toISOString().slice(0, 10));
    d.setDate(d.getDate() + 1);
  }
  return out;
}

/** 심볼 + 날짜 시드로 결정론적 가격 시퀀스 생성 (스텁) */
function stubPrices(symbol: string, dates: string[]): OHLCVRow[] {
  let seed = 0;
  for (let i = 0; i < symbol.length; i++) seed += symbol.charCodeAt(i);
  let close = 100 + (seed % 50);
  const rows: OHLCVRow[] = [];
  for (const date of dates) {
    const daySeed = date.split("-").map(Number).reduce((a, b) => a + b, 0);
    const change = ((seed * 17 + daySeed * 31) % 101) / 100 - 0.5;
    const pct = 1 + change * 0.02;
    const open = close;
    close = Math.round(open * pct * 100) / 100;
    const high = Math.max(open, close) * (1 + Math.abs(change) * 0.005);
    const low = Math.min(open, close) * (1 - Math.abs(change) * 0.005);
    const volume = 1_000_000 + (daySeed * 1000) % 5_000_000;
    rows.push({
      date,
      open,
      high: Math.round(high * 100) / 100,
      low: Math.round(low * 100) / 100,
      close,
      volume,
    });
  }
  return rows;
}

export async function getHistory(
  symbol: string,
  start: string,
  end: string,
  _interval = "d"
): Promise<OHLCVRow[]> {
  const startD = new Date(start);
  const endD = new Date(end);
  const dates = businessDaysBetween(startD, endD);
  return stubPrices(symbol.toUpperCase(), dates);
}

/** close 배열로 RSI(period) 계산. 앞 (period)개는 null. */
export function computeRSI(closes: number[], period: number): (number | null)[] {
  const out: (number | null)[] = [];
  for (let i = 0; i < closes.length; i++) {
    if (i < period) {
      out.push(null);
      continue;
    }
    let gainSum = 0;
    let lossSum = 0;
    for (let j = i - period + 1; j <= i; j++) {
      const ch = closes[j]! - closes[j - 1]!;
      if (ch > 0) gainSum += ch;
      else lossSum -= ch;
    }
    const avgGain = gainSum / period;
    const avgLoss = lossSum / period;
    if (avgLoss === 0) {
      out.push(100);
      continue;
    }
    const rs = avgGain / avgLoss;
    const rsi = 100 - 100 / (1 + rs);
    out.push(Math.round(rsi * 100) / 100);
  }
  return out;
}
