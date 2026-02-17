"""
forecast.py - 과거 주가 기반 가격 예측 (일봉, 퀀트지표 반영)

- 과거 데이터 → 퀀트 지표(RSI, MACD 등) 계산
- 퀀트 지표 + 종가 → 예측 모델
- 과거: 실제 vs 예측(in-sample fit) 비교, 미래: 예측만 표시

"""

import os
import json
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
import yfinance as yf

# Optional: statsmodels for ARIMA
try:
    from statsmodels.tsa.arima.model import ARIMA
    HAS_ARIMA = True
except ImportError:
    HAS_ARIMA = False

# Optional: Prophet
try:
    from prophet import Prophet
    HAS_PROPHET = True
except ImportError:
    HAS_PROPHET = False


from util import path_for, load_json_file

WATCHLIST_PATH = os.environ.get('WATCHLIST_PATH', path_for('watchlist.json'))
FORECAST_DAYS = int(os.environ.get('FORECAST_DAYS', 30))
DEFAULT_MODEL = os.environ.get('FORECAST_MODEL', 'arima').lower()
NANOQUANT_DB = os.environ.get('NANOQUANT_DB', path_for('nanoquant_v1.db'))


def load_watchlist() -> List[str]:
    """
    등록 티커 목록 로드. 환경변수 WATCHLIST가 있으면 우선 사용.
    """
    watch_env = os.environ.get('WATCHLIST', '').strip()
    if watch_env:
        return [t.strip().upper() for t in watch_env.split(',') if t.strip()]
    data = load_json_file(WATCHLIST_PATH)
    if data:
        if isinstance(data, list):
            return [str(t).upper() for t in data]
        if isinstance(data, dict) and 'tickers' in data:
            return [str(t).upper() for t in data['tickers']]
    return []


def _get_db():
    """TradingDatabase 인스턴스 (forecast용)."""
    from core import TradingDatabase
    return TradingDatabase(NANOQUANT_DB)


def fetch_daily_bars(ticker: str, days: int = 252, use_db: bool = True) -> pd.DataFrame:
    """
    일봉 조회: DB에서만 조회. 없으면 yfinance로 가져와 DB 저장 후 반환.
    """
    if use_db:
        try:
            db = _get_db()
            df = db.get_daily_bars(ticker, days=days)
            if df is not None and len(df) > 0:
                return df
        except Exception:
            pass
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period='1y', interval='1d')
        if df is None or df.empty or len(df) < 10:
            return pd.DataFrame()
        df = df.tail(days)
        df.reset_index(inplace=True)
        df.columns = [str(c).lower() if str(c) != 'Datetime' else 'timestamp' for c in df.columns]
        if 'date' in df.columns and 'timestamp' not in df.columns:
            df['timestamp'] = df['date']
        if use_db and len(df) >= 10:
            try:
                _get_db().save_daily_bars(ticker, df)
            except Exception:
                pass
        return df
    except Exception:
        return pd.DataFrame()


def backfill_daily_bars_for_watchlist(days: int = 252) -> Dict[str, int]:
    """
    watchlist 티커 전체에 대해 일봉을 한 번에 가져와 DB에 저장.
    Returns: { ticker: 저장된 행 수 }
    """
    tickers = load_watchlist()
    if not tickers:
        return {}
    out = {}
    db = _get_db()
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period='1y', interval='1d')
            if df is None or df.empty or len(df) < 5:
                out[ticker] = 0
                continue
            df = df.tail(days)
            df.reset_index(inplace=True)
            df.columns = [str(c).lower() if str(c) != 'Datetime' else 'timestamp' for c in df.columns]
            if 'date' in df.columns and 'timestamp' not in df.columns:
                df['timestamp'] = df['date']
            n = db.save_daily_bars(ticker, df)
            out[ticker] = n
        except Exception as e:
            out[ticker] = 0
    return out


def _compute_quant_series(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    일봉 OHLCV에서 RSI, MACD histogram 시계열 계산.
    Returns DataFrame with columns: rsi, macd_hist (NaN은 forward-fill 후 backward-fill)
    """
    if df.empty or 'close' not in df.columns:
        return None
    close = df['close'].astype(float)
    n = len(close)
    if n < 35:  # MACD needs 26+9
        return None
    # RSI series (period=14)
    period = 14
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    rsi_series = 100 - (100 / (1 + rs))
    # MACD histogram series
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist = macd_line - signal_line
    out = pd.DataFrame({'rsi': rsi_series, 'macd_hist': macd_hist}, index=df.index)
    out = out.ffill().bfill()
    return out


def forecast_ma(series: pd.Series, steps: int, window: int = 20) -> np.ndarray:
    """지수이동평균(EMA) 스타일: 최근에 더 높은 가중치."""
    n = len(series)
    if n < 2:
        return np.full(steps, float(series.iloc[-1]) if n else 0)
    window = min(window, max(5, n // 2))
    # EMA: alpha=2/(window+1)
    alpha = 2 / (window + 1)
    ema = series.iloc[0]
    for v in series.iloc[1:]:
        ema = alpha * v + (1 - alpha) * ema
    return np.full(steps, float(ema))


def forecast_linear(series: pd.Series, steps: int) -> np.ndarray:
    """가중치 선형 회귀: 최근 데이터에 높은 가중치. 최근 추세 반영."""
    n = len(series)
    if n < 2:
        return np.full(steps, float(series.iloc[-1]) if n else 0)
    x = np.arange(n, dtype=float)
    y = series.values.astype(float)
    # 최근 30% 구간에 70% 가중치 (decay: 오래된 것일수록 낮은 가중치)
    half_life = max(3, n // 3)
    w = np.exp(-0.693 * (n - 1 - np.arange(n)) / half_life)
    w = w / w.sum()
    # 가중 최소제곱: slope = sum(w*x*y)/sum(w*x^2) - weighted mean 형태
    xm = np.sum(w * x)
    ym = np.sum(w * y)
    slope = np.sum(w * (x - xm) * (y - ym)) / (np.sum(w * (x - xm) ** 2) + 1e-10)
    last_val = float(y[-1])
    return np.array([last_val + slope * (i + 1) for i in range(steps)])


def forecast_arima(series: pd.Series, steps: int) -> np.ndarray:
    """ARIMA 예측. 적은 데이터는 (0,1,1), 그 외 (2,1,2)."""
    if not HAS_ARIMA or len(series) < 6:
        return forecast_linear(series, steps)
    try:
        n = len(series)
        order = (0, 1, 1) if n < 20 else (2, 1, 2)
        model = ARIMA(series.astype(float), order=order)
        fitted = model.fit()
        fc = fitted.forecast(steps=steps)
        return np.asarray(fc)
    except Exception:
        return forecast_linear(series, steps)


def _forecast_with_quant(
    df: pd.DataFrame, steps: int, model: str
) -> Tuple[List[float], List[float]]:
    """
    퀀트 지표(RSI, MACD)를 포함한 예측.
    Returns: (fitted: 과거 구간 in-sample 예측값, forecast: 미래 구간 예측값)
    """
    close = df['close'].astype(float)
    n = len(close)
    quant = _compute_quant_series(df)
    exog_available = quant is not None and len(quant.dropna()) >= 20

    # 퀀트 지표 없거나 모델이 ma: 기존 방식 + in-sample fitted 계산
    if not exog_available or model == 'ma':
        if model == 'ma':
            pred_fc = forecast_ma(close, steps)
            window = min(20, max(5, n // 2))
            alpha = 2 / (window + 1)
            ema_s = close.ewm(alpha=2 / (window + 1), adjust=False).mean()
            fitted = list(ema_s.values)
        elif model == 'linear':
            pred_fc = forecast_linear(close, steps)
            x = np.arange(n, dtype=float)
            y = close.values.astype(float)
            slope = np.polyfit(x, y, 1)[0]
            intercept = np.polyfit(x, y, 1)[1]
            fitted = [float(intercept + slope * i) for i in range(n)]
        elif model == 'arima' and HAS_ARIMA:
            try:
                order = (0, 1, 1) if n < 20 else (2, 1, 2)
                m = ARIMA(close.astype(float), order=order)
                res = m.fit()
                fitted = list(res.fittedvalues)
                pred_fc = res.forecast(steps=steps)
            except Exception:
                pred_fc = forecast_arima(close, steps)
                fitted = list(close.values)
        elif model == 'prophet' and HAS_PROPHET:
            try:
                prep = pd.DataFrame({'ds': pd.to_datetime(df['timestamp'] if 'timestamp' in df.columns else df.index), 'y': close.values})
                m = Prophet(daily_seasonality=True, yearly_seasonality=True)
                m.fit(prep)
                pred_hist = m.predict(prep[['ds']])
                fitted = list(pred_hist['yhat'].values)
                future = m.make_future_dataframe(periods=steps, freq='D')
                pred_fut = m.predict(future)
                pred_fc = pred_fut['yhat'].tail(steps).values
            except Exception:
                pred_fc = forecast_prophet(close, steps, freq='D')
                fitted = list(close.values)
        else:
            pred_fc = forecast_linear(close, steps)
            fitted = list(close.values)
        return fitted, [float(x) for x in pred_fc]

    # 퀀트 지표 사용
    rsi = quant['rsi'].values.astype(float)
    macd_hist = quant['macd_hist'].values.astype(float)
    exog = np.column_stack([rsi, macd_hist])
    exog = np.nan_to_num(exog, nan=50.0, posinf=50.0, neginf=50.0)

    fitted_vals = []
    forecast_vals = []

    if model == 'arima' and HAS_ARIMA:
        try:
            order = (0, 1, 1) if n < 40 else (2, 1, 2)
            arima_m = ARIMA(close.values, exog=exog, order=order)
            res = arima_m.fit()
            fitted_vals = list(res.fittedvalues)
            exog_future = np.tile(exog[-1], (steps, 1))
            fc = res.forecast(steps=steps, exog=exog_future)
            forecast_vals = [float(x) for x in fc]
        except Exception:
            pred_fc = forecast_arima(close, steps)
            fitted_vals = list(close.values)
            forecast_vals = [float(x) for x in pred_fc]
        return fitted_vals, forecast_vals

    if model == 'prophet' and HAS_PROPHET:
        try:
            prep = pd.DataFrame({
                'ds': pd.to_datetime(df['timestamp'] if 'timestamp' in df.columns else df.index),
                'y': close.values,
                'rsi': rsi,
                'macd': macd_hist,
            })
            m = Prophet(daily_seasonality=True, yearly_seasonality=True)
            m.add_regressor('rsi')
            m.add_regressor('macd')
            m.fit(prep)
            pred_hist = m.predict(prep[['ds', 'rsi', 'macd']])
            fitted_vals = list(pred_hist['yhat'].values)
            future = m.make_future_dataframe(periods=steps, freq='D')
            # 과거 구간은 실제 rsi/macd, 미래 구간은 마지막값 유지
            future['rsi'] = list(rsi) + [rsi[-1]] * steps
            future['macd'] = list(macd_hist) + [macd_hist[-1]] * steps
            pred_fut = m.predict(future)
            forecast_vals = [float(x) for x in pred_fut['yhat'].tail(steps).values]
        except Exception:
            pred_fc = forecast_prophet(close, steps, freq='D')
            fitted_vals = list(close.values)
            forecast_vals = [float(x) for x in pred_fc]
        return fitted_vals, forecast_vals

    if model == 'linear':
        # 다변량 선형: close ~ time + rsi + macd
        x_mat = np.column_stack([
            np.arange(n),
            rsi,
            macd_hist,
        ])
        x_mat = np.nan_to_num(x_mat, nan=0)
        y = close.values
        w = np.exp(-0.3 * (n - 1 - np.arange(n)))
        w = w / w.sum()
        coeffs = np.linalg.lstsq(
            (x_mat.T * w).T, y * w, rcond=None
        )[0]
        fitted_vals = list((x_mat @ coeffs))
        last_rsi, last_macd = rsi[-1], macd_hist[-1]
        for i in range(steps):
            x_fut = np.array([n + i, last_rsi, last_macd])
            forecast_vals.append(float(x_fut @ coeffs))
        return fitted_vals, forecast_vals

    pred_fc = forecast_linear(close, steps)
    return list(close.values), [float(x) for x in pred_fc]


def forecast_prophet(series: pd.Series, steps: int, freq: str = 'D') -> np.ndarray:
    """Prophet 예측. 일봉 30개 이상에서 동작."""
    min_len = 30
    if not HAS_PROPHET or len(series) < min_len:
        return forecast_linear(series, steps)
    try:
        df = series.reset_index()
        df.columns = ['ds', 'y']
        df['ds'] = pd.to_datetime(df['ds'])
        m = Prophet(daily_seasonality=(freq == 'D'), yearly_seasonality=True)
        m.fit(df)
        future = m.make_future_dataframe(periods=steps, freq=freq)
        pred = m.predict(future)
        return pred['yhat'].tail(steps).values
    except Exception:
        return forecast_linear(series, steps)


def get_forecast_data(
    ticker: str,
    model: str = 'linear',
    forecast_days: int = None,
    df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    과거 + 예측 구간 데이터 반환 (차트용, 일봉만).

    Args:
        ticker: 종목 심볼
        model: 'ma' | 'linear' | 'arima' | 'prophet'
        forecast_days: 일봉 예측 일수

    Returns:
        {
          'labels': ['2024-01-01', ...],   # 과거 날짜
          'actual': [100.0, ...],          # 실제 종가
          'fitted': [99.5, ...],           # 과거 구간 in-sample 예측 (실제 vs 예측 비교용)
          'forecast': [101.0, ...],        # 미래 구간 예측
          'labels_forecast': [...],        # 미래 날짜
          'ticker', 'model', 'error'
        }
    """
    forecast_days = forecast_days or FORECAST_DAYS
    model = (model or DEFAULT_MODEL).lower()
    if model not in ('ma', 'linear', 'arima', 'prophet'):
        model = 'linear'

    out = {
        'labels': [],
        'actual': [],
        'fitted': [],
        'forecast': [],
        'labels_forecast': [],
        'ticker': ticker,
        'model': model,
        'error': None,
    }

    if df is None:
        df = fetch_daily_bars(ticker)
    if df.empty:
        out['error'] = '데이터 없음'
        return out

    close_col = 'close' if 'close' in df.columns else 'Close'
    if close_col not in df.columns:
        out['error'] = 'close 컬럼 없음'
        return out

    steps = forecast_days

    series = df[close_col].dropna()
    if len(series) < 5:
        out['error'] = '데이터 부족'
        return out

    # 날짜 레이블
    ts_col = 'timestamp' if 'timestamp' in df.columns else 'date'
    dates = pd.to_datetime(df[ts_col]).tolist()
    out['labels'] = [d.strftime('%Y-%m-%d') for d in dates]
    out['actual'] = [float(x) for x in series.tolist()]

    # 퀀트 지표 반영 예측 (fitted: 과거 in-sample, forecast: 미래)
    fitted, forecast = _forecast_with_quant(df, steps, model)
    out['fitted'] = [float(x) for x in fitted]
    out['forecast'] = [float(x) for x in forecast]

    # 미래 날짜 레이블
    last_d = pd.to_datetime(out['labels'][-1])
    out['labels_forecast'] = [
        (last_d + timedelta(days=i + 1)).strftime('%Y-%m-%d')
        for i in range(len(forecast))
    ]

    return out


def _make_data_hash(df: pd.DataFrame) -> str:
    """daily_bars 변경 감지용 해시. 마지막 날짜 + 행 수."""
    if df.empty or 'timestamp' not in df.columns:
        return ''
    ts = df['timestamp'].iloc[-1]
    d = pd.to_datetime(ts).strftime('%Y-%m-%d')
    return f"{d}:{len(df)}"


def get_forecast_chart_payload(ticker: str, model: str = 'linear') -> Dict[str, Any]:
    """
    Chart.js용: 실제 vs 예측(퀀트 기반) 비교.
    DB 캐시 우선 조회. 없으면 계산 후 저장.
    """
    df = fetch_daily_bars(ticker)
    if df.empty:
        return {'error': '데이터 없음'}
    data_hash = _make_data_hash(df)

    # 캐시 조회
    try:
        db = _get_db()
        cached = db.get_forecast_cache(ticker, model, data_hash)
        if cached is not None and not cached.get('error'):
            return cached
    except Exception:
        pass

    # 계산 (df 이미 로드됨)
    data = get_forecast_data(ticker, model=model, df=df)
    if data.get('error'):
        return data
    n_a = len(data['actual'])
    n_f = len(data['forecast'])
    fitted = data.get('fitted', [])
    forecast = data.get('forecast', [])
    labels_forecast = data.get('labels_forecast', [])

    data['labels_full'] = data['labels'] + labels_forecast
    data['actual_full'] = data['actual'] + [None] * n_f
    data['predicted_full'] = (fitted if len(fitted) == n_a else data['actual']) + forecast
    data['forecast_full'] = [None] * n_a + forecast

    # 캐시 저장
    try:
        _get_db().save_forecast_cache(ticker, model, data_hash, data)
    except Exception:
        pass

    return data


if __name__ == '__main__':
    """watchlist 티커 일봉을 한 번에 가져와 DB에 저장. 예: python forecast.py"""
    print("Backfilling daily bars for watchlist...")
    result = backfill_daily_bars_for_watchlist()
    for t, n in sorted(result.items()):
        print(f"  {t}: {n} rows")
    print(f"Done. Total tickers: {len(result)}")
