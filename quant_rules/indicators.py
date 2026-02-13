"""
quant_rules/indicators.py - 기술적 지표 계산 함수

OHLCV 시계열(15분봉 등)을 입력받아 퀀트 트레이딩에 사용하는 기술적 지표를 계산합니다.

입력 형식:
  - pandas DataFrame (columns: open, high, low, close, volume)
  - List[Dict] with keys: open, high, low, close, volume

사용처:
  - Layer 2: stock_data에 quant_indicators로 저장
  - Layer 3: Deep Agent LLM 프롬프트에 포함 (사유 추론에 반영)
  - DB 뷰어: RSI, SMA, MACD, BB%B, Vol비율 컬럼으로 표시
"""

from typing import Dict, List, Optional, Tuple, Union
import pandas as pd


def _to_df(data: Union[pd.DataFrame, List[Dict]]) -> pd.DataFrame:
    """OHLCV 데이터를 DataFrame으로 정규화"""
    if isinstance(data, pd.DataFrame):
        df = data.copy()
    elif isinstance(data, list) and data and isinstance(data[0], dict):
        df = pd.DataFrame(data)
    else:
        return pd.DataFrame()

    # 컬럼명 정규화 (소문자)
    df.columns = [str(c).lower() for c in df.columns]
    if df.empty or 'close' not in df.columns:
        return pd.DataFrame()
    return df


def rsi(
    data: Union[pd.DataFrame, List[Dict]],
    period: int = 14
) -> Optional[float]:
    """
    RSI (Relative Strength Index) - 상대 강도 지수

    가격 상승/하락의 상대적 강도를 0~100 사이로 정규화합니다.
    과매수/과매도 판단에 활용됩니다.

    공식:
        RS = avg_gain / avg_loss  (기간 내 평균 상승폭 / 평균 하락폭)
        RSI = 100 - (100 / (1 + RS))

    해석:
        - RSI < 30: 과매도 구간, 반등 가능성
        - RSI > 70: 과매수 구간, 조정 가능성
        - RSI 50 근처: 중립
        - RSI 30~70: 일반적 구간

    Args:
        data: OHLCV 시계열 (DataFrame 또는 List[Dict])
        period: RSI 기간 (기본 14, Wilder 권장)

    Returns:
        최근 RSI 값 (0~100), 데이터 부족 시 None
    """
    df = _to_df(data)
    if len(df) < period + 1:
        return None

    close = df['close'].astype(float)
    delta = close.diff()

    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, 1e-10)
    rsi_val = 100 - (100 / (1 + rs))

    return float(rsi_val.iloc[-1])


def sma(
    data: Union[pd.DataFrame, List[Dict]],
    period: int = 20,
    column: str = 'close'
) -> Optional[float]:
    """
    SMA (Simple Moving Average) - 단순이동평균

    지정 기간 내 종가(또는 지정 컬럼)의 산술평균입니다.
    추세의 평균 가격 수준을 나타냅니다.

    공식:
        SMA = (P1 + P2 + ... + Pn) / n

    해석:
        - 현재가 > SMA: 상승 추세
        - 현재가 < SMA: 하락 추세
        - SMA는 지지/저항선으로 활용 가능

    Args:
        data: OHLCV 시계열
        period: 이동평균 기간 (기본 20)
        column: 적용할 가격 컬럼 (close, open, high, low)

    Returns:
        최근 SMA 값, 데이터 부족 시 None
    """
    df = _to_df(data)
    if len(df) < period or column not in df.columns:
        return None

    series = df[column].astype(float)
    return float(series.rolling(window=period).mean().iloc[-1])


def ema(
    data: Union[pd.DataFrame, List[Dict]],
    period: int = 12,
    column: str = 'close'
) -> Optional[float]:
    """
    EMA (Exponential Moving Average) - 지수이동평균

    최근 데이터에 더 높은 가중치를 부여하는 이동평균입니다.
    SMA보다 가격 변동에 민감하게 반응합니다.

    공식:
        EMA_today = (Close_today * α) + (EMA_yesterday * (1 - α))
        α = 2 / (period + 1)

    해석:
        - EMA12 > EMA26: 단기 상승 추세 (골든 크로스)
        - EMA12 < EMA26: 단기 하락 추세 (데드 크로스)
        - MACD 계산의 기본 요소

    Args:
        data: OHLCV 시계열
        period: EMA 기간 (기본 12, MACD fast와 동일)
        column: 적용할 가격 컬럼

    Returns:
        최근 EMA 값, 데이터 부족 시 None
    """
    df = _to_df(data)
    if len(df) < period or column not in df.columns:
        return None

    series = df[column].astype(float)
    ema_val = series.ewm(span=period, adjust=False).mean()
    return float(ema_val.iloc[-1])


def macd(
    data: Union[pd.DataFrame, List[Dict]],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> Optional[Dict[str, float]]:
    """
    MACD (Moving Average Convergence Divergence) - 추세·모멘텀 지표

    두 EMA의 차이를 통해 추세 강도와 방향을 파악합니다.

    공식:
        MACD Line = EMA(fast) - EMA(slow)
        Signal Line = EMA(MACD Line, signal)
        Histogram = MACD Line - Signal Line

    해석:
        - Histogram > 0: 상승 모멘텀 (매수 신호 경향)
        - Histogram < 0: 하락 모멘텀 (매도 신호 경향)
        - Histogram 절대값: 모멘텀 강도
        - MACD가 Signal을 상향 돌파: 골든 크로스
        - MACD가 Signal을 하향 돌파: 데드 크로스

    Args:
        data: OHLCV 시계열
        fast: 빠른 EMA 기간 (기본 12)
        slow: 느린 EMA 기간 (기본 26)
        signal: 시그널 라인 EMA 기간 (기본 9)

    Returns:
        {'macd': float, 'signal': float, 'histogram': float}
        최소 slow+signal 봉 필요, 데이터 부족 시 None
    """
    df = _to_df(data)
    if len(df) < slow + signal:
        return None

    close = df['close'].astype(float)

    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()

    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    return {
        'macd': float(macd_line.iloc[-1]),
        'signal': float(signal_line.iloc[-1]),
        'histogram': float(histogram.iloc[-1]),
    }


def bollinger_bands(
    data: Union[pd.DataFrame, List[Dict]],
    period: int = 20,
    std_dev: float = 2.0
) -> Optional[Dict[str, float]]:
    """
    Bollinger Bands - 변동성 기반 가격 밴드

    가격이 통계적 범위 내에서 어디에 위치하는지 나타냅니다.
    과매수/과매도 및 변동성 파악에 사용됩니다.

    공식:
        Middle = SMA(close, period)
        Upper = Middle + (std_dev * 표준편차)
        Lower = Middle - (std_dev * 표준편차)
        %B = (현재가 - Lower) / (Upper - Lower)

    해석:
        - %B > 1: 상단 밴드 위 (과매수)
        - %B < 0: 하단 밴드 아래 (과매도)
        - %B 0.5: 중간 밴드 위치
        - bandwidth: 변동성 크기 (좁을수록 변동성 수축 → 돌파 임박)

    Args:
        data: OHLCV 시계열
        period: 중간선 SMA 기간 (기본 20)
        std_dev: 표준편차 배수 (기본 2.0)

    Returns:
        {'upper', 'middle', 'lower', 'bandwidth', 'pct_b'}
        pct_b: 0=하단, 0.5=중간, 1=상단 (1 초과/0 미만 가능)
    """
    df = _to_df(data)
    if len(df) < period:
        return None

    close = df['close'].astype(float)

    middle = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)

    # %B = (현재가 - 하단밴드) / (상단밴드 - 하단밴드)
    band_width = upper.iloc[-1] - lower.iloc[-1]
    pct_b = (close.iloc[-1] - lower.iloc[-1]) / band_width if band_width > 0 else 0.5

    return {
        'upper': float(upper.iloc[-1]),
        'middle': float(middle.iloc[-1]),
        'lower': float(lower.iloc[-1]),
        'bandwidth': float(band_width),
        'pct_b': float(pct_b),
    }


def price_momentum(
    data: Union[pd.DataFrame, List[Dict]],
    periods: int = 5,
    direction: bool = True
) -> Optional[Tuple[float, float]]:
    """
    Price Momentum - 가격 변동률 (Rate of Change)

    N봉 전 대비 현재가의 변동률을 계산합니다.
    단기 추세 방향과 강도를 파악하는 데 사용됩니다.

    공식:
        Momentum % = (Close_now - Close_n_periods_ago) / Close_n_periods_ago * 100
        Direction = 1 (상승) or -1 (하락)

    해석:
        - Momentum > 0, Direction 1: 상승 추세
        - Momentum < 0, Direction -1: 하락 추세
        - 절대값이 클수록 변동이 큼

    Args:
        data: OHLCV 시계열
        periods: 비교할 기간 수, 봉 개수 (기본 5)
        direction: True면 (변동률%, 방향) 반환, False면 (변동률%, None)

    Returns:
        (변동률 퍼센트, 1=상승/-1=하락) 또는 (변동률%, None)
    """
    df = _to_df(data)
    if len(df) < periods + 1:
        return None

    close = df['close'].astype(float)
    current = close.iloc[-1]
    past = close.iloc[-(periods + 1)]

    if past == 0:
        return None

    change_pct = (current - past) / past * 100

    if direction:
        direction_val = 1 if current > past else -1
        return (float(change_pct), direction_val)
    return (float(change_pct), None)


def volume_ratio(
    data: Union[pd.DataFrame, List[Dict]],
    current_periods: int = 1,
    avg_periods: int = 20
) -> Optional[float]:
    """
    Volume Ratio - 거래량 비율

    현재 거래량이 과거 평균 대비 몇 배인지 계산합니다.
    가격 변동의 신뢰도(참여도)를 판단하는 데 사용됩니다.

    공식:
        Current Vol = 최근 current_periods 봉의 거래량 합
        Avg Vol = 그 이전 avg_periods 봉의 평균 거래량
        Volume Ratio = Current Vol / Avg Vol

    해석:
        - > 1.5x: 거래량 급증, 추세 확인 신호
        - > 2.0x: 강한 관심, 돌파 가능성
        - < 0.5x: 거래량 저조, 추세 약함
        - 가격 변동 + 거래량 증가: 추세 유효성 높음

    Args:
        data: OHLCV 시계열 (volume 컬럼 필요)
        current_periods: 현재 거래량에 사용할 최근 봉 개수 (기본 1)
        avg_periods: 평균 계산 기간 (기본 20)

    Returns:
        현재/평균 거래량 배수 (예: 2.5 = 평균의 2.5배)
    """
    df = _to_df(data)
    if 'volume' not in df.columns or len(df) < avg_periods:
        return None

    vol = df['volume'].astype(float)

    current_vol = vol.iloc[-current_periods:].sum()
    avg_vol = vol.iloc[-avg_periods:-current_periods].mean() if avg_periods > current_periods else vol.iloc[:-current_periods].mean()

    if avg_vol == 0:
        return None

    return float(current_vol / avg_vol)


def compute_all(
    data: Union[pd.DataFrame, List[Dict]],
    rsi_period: int = 14,
    sma_period: int = 20,
    bb_period: int = 20,
    momentum_periods: int = 5,
) -> Dict[str, Optional[Union[float, Dict]]]:
    """
    모든 퀀트 지표를 한 번에 계산

    Layer 2에서 stock_data 생성 시 호출되며, Layer 3 LLM 프롬프트와 DB 뷰어에 사용됩니다.

    반환 키:
        - rsi: RSI (0~100)
        - sma_20: SMA(20)
        - ema_12, ema_26: EMA 값
        - macd: {macd, signal, histogram}
        - bollinger: {upper, middle, lower, bandwidth, pct_b}
        - momentum: [변동률%, 방향 1/-1]
        - volume_ratio: 거래량 배수

    최소 데이터: MACD는 26+9=35봉, RSI는 15봉 이상 권장 (40봉 추천)

    Args:
        data: OHLCV 시계열
        rsi_period: RSI 기간 (기본 14)
        sma_period: SMA/볼린저 기간 (기본 20)
        bb_period: Bollinger Bands 기간 (기본 20)
        momentum_periods: 모멘텀 비교 기간 (기본 5)

    Returns:
        {'rsi', 'sma_20', 'ema_12', 'ema_26', 'macd', 'bollinger', 'momentum', 'volume_ratio'}
        계산 불가 시 해당 키의 값은 None
    """
    return {
        'rsi': rsi(data, period=rsi_period),
        'sma_20': sma(data, period=sma_period),
        'ema_12': ema(data, period=12),
        'ema_26': ema(data, period=26),
        'macd': macd(data),
        'bollinger': bollinger_bands(data, period=bb_period),
        'momentum': price_momentum(data, periods=momentum_periods),
        'volume_ratio': volume_ratio(data),
    }


def compute_all_multi(
    bars: Dict[str, Union[pd.DataFrame, List[Dict]]]
) -> Dict[str, Dict[str, Optional[Union[float, Dict]]]]:
    """
    타임프레임별 OHLCV에 대해 퀀트 지표 계산 (동적 처리, 유지보수 용이)

    Args:
        bars: { '15m': [...], '1h': [...], '1d': [...] } 형태.
              키는 타임프레임 식별자. 새 구간 추가 시 키만 추가하면 됨.

    Returns:
        { '15m': {rsi, sma_20, ...}, '1h': {...}, '1d': {...} }
    """
    result = {}
    for label, data in (bars or {}).items():
        if data is None or (isinstance(data, list) and len(data) < 2):
            result[label] = {}
            continue
        result[label] = compute_all(data)
    return result
