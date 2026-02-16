"""
data_fetcher.py - Market data fetcher using yfinance (free, no API key needed)
"""

import os
import sys

# Windows: if project path has non-ASCII (e.g. Korean), certifi's cacert.pem path
# breaks curl/OpenSSL (error 77). Copy cert to an ASCII-only path before loading yfinance.
def _fix_ssl_cert_path_on_windows():
    if sys.platform != "win32":
        return
    try:
        import certifi
        import shutil
        path = certifi.where()
        if not path or (isinstance(path, str) and path.isascii()):
            return
        dest_dir = os.environ.get("TEMP") or os.environ.get("TMP") or os.path.expandvars("%TEMP%")
        if not dest_dir or not dest_dir.isascii():
            dest_dir = os.path.join(os.environ.get("SYSTEMROOT", "C:\\Windows"), "Temp")
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, "nanoquant_cacert.pem")
        shutil.copy2(path, dest)
        os.environ["SSL_CERT_FILE"] = dest
        os.environ["REQUESTS_CA_BUNDLE"] = dest
    except Exception:
        pass

_fix_ssl_cert_path_on_windows()

import yfinance as yf
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import pandas as pd

# 타임프레임 설정: (interval, periods, max_days or period_str)
# 유지보수: 새 구간 추가 시 여기만 수정
INTERVAL_CONFIG: Dict[str, Tuple[int, Optional[int], Optional[str]]] = {
    '15m': (40, 7, None),   # periods, max_days, period_str
    '1h': (40, 60, None),
    '1d': (30, None, '2mo'),
}
TIMEFRAMES = list(INTERVAL_CONFIG.keys())


class DataFetcher:
    """Fetches market data using yfinance"""

    def __init__(self):
        """Initialize data fetcher"""
        pass

    def get_bars(
        self,
        ticker: str,
        interval: str,
        periods: int = None
    ) -> pd.DataFrame:
        """
        OHLCV 봉 데이터 조회 (단일 진입점, 유지보수 용이)

        Args:
            ticker: 종목 심볼
            interval: 봉 간격 ('15m', '1h', '1d' 등). INTERVAL_CONFIG에 정의된 값 사용.
            periods: 조회 봉 수 (None이면 INTERVAL_CONFIG 기본값 사용)

        Returns:
            OHLCV DataFrame
        """
        if interval not in INTERVAL_CONFIG:
            print(f"Unknown interval '{interval}'. Use one of: {TIMEFRAMES}")
            return pd.DataFrame()

        default_periods, max_days, period_str = INTERVAL_CONFIG[interval]
        periods = periods if periods is not None else default_periods

        try:
            stock = yf.Ticker(ticker)
            end = datetime.now()

            if period_str:
                df = stock.history(period=period_str, interval=interval)
            else:
                start = end - timedelta(days=max_days)
                df = stock.history(start=start, end=end, interval=interval)

            if df is None or not isinstance(df, pd.DataFrame) or df.empty:
                return pd.DataFrame()

            df.reset_index(inplace=True)
            df.columns = [str(col).lower() if str(col) != 'Datetime' else 'timestamp' for col in df.columns]
            return df.tail(periods)

        except Exception as e:
            print(f"Error fetching {interval} bars for {ticker}: {str(e)}")
            return pd.DataFrame()

    def get_current_price(self, ticker: str) -> Optional[float]:
        """
        Get current price for a ticker

        Args:
            ticker: Stock ticker symbol

        Returns:
            Current price or None
        """
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period='1d', interval='1m')

            if data is None or not isinstance(data, pd.DataFrame) or data.empty:
                return None
            # Column may be 'Close' or 'close' depending on yfinance/pandas
            close_col = 'Close' if 'Close' in data.columns else 'close'
            if close_col not in data.columns:
                return None
            return float(data[close_col].iloc[-1])

        except Exception as e:
            print(f"Error fetching current price for {ticker}: {str(e)}")
            return None

    def get_volume_data(
        self,
        ticker: str,
        current_period_minutes: int = 15
    ) -> Dict[str, float]:
        """
        Get volume data including current and 5-day average

        Args:
            ticker: Stock ticker symbol
            current_period_minutes: Minutes for current period

        Returns:
            Dict with 'current_volume' and 'avg_volume'
        """
        # Get recent bars (15m, 5 days worth)
        bars_df = self.get_bars(ticker, '15m', periods=5 * 24 * 4)

        if bars_df is None or bars_df.empty:
            return {'current_volume': 0, 'avg_volume': 0}

        vol_col = 'volume' if 'volume' in bars_df.columns else 'Volume'
        if vol_col not in bars_df.columns:
            return {'current_volume': 0, 'avg_volume': 0}

        # Current period volume (latest bar)
        current_volume = float(bars_df.iloc[-1][vol_col]) if len(bars_df) > 0 else 0

        # Average volume (exclude current bar)
        avg_volume = float(bars_df.iloc[:-1][vol_col].mean()) if len(bars_df) > 1 else current_volume

        return {
            'current_volume': current_volume,
            'avg_volume': avg_volume
        }

    def scan_small_caps(
        self,
        min_price: float = 1.0,
        max_price: float = 50.0,
        limit: int = 100
    ) -> List[str]:
        """
        Scan for small-cap stocks

        Note: This returns a curated list of popular small-cap stocks.
        For production, you would integrate with a screener API.

        Args:
            min_price: Minimum stock price
            max_price: Maximum stock price
            limit: Maximum number of stocks to return

        Returns:
            List of ticker symbols
        """
        # Curated list of US small-cap stocks
        # In production, you could:
        # 1. Use yfinance to download S&P 600 (small-cap index) constituents
        # 2. Use a stock screener API (e.g., finviz, yahoo finance screener)
        # 3. Maintain your own database of small-caps

        small_cap_universe = [
            # Recent IPOs and growth stocks
            'SOFI', 'HOOD', 'COIN', 'RBLX', 'DASH',
            'ABNB', 'SNOW', 'DKNG', 'PLTR', 'RIVN',

            # EV and clean energy
            'LCID', 'NIO', 'PLUG', 'FCEL', 'BLNK',

            # Biotech small-caps
            'SNDL', 'TLRY', 'CGC', 'ACB', 'CRON',

            # Crypto-related
            'MARA', 'RIOT', 'BTBT', 'HUT', 'CLSK',

            # Tech small-caps
            'WISH', 'CLOV', 'SKLZ', 'OPEN', 'UPST',

            # Consumer/Retail
            'BEYOND', 'BYND', 'PTON', 'W', 'CHWY',

            # Additional small-caps
            'SPCE', 'ASTR', 'RDW', 'IONQ', 'QUBT',

            # Meme / Retail
            'GME', 'AMC',

            # AI / Semiconductor
            'SMCI', 'SOUN', 'BBAI',

            # Crypto / Bitcoin
            'MSTR',

            # EV China
            'XPEV', 'LI',

            # Space
            'RKLB', 'ASTS', 'LUNR',

            # Flying car / Mobility
            'JOBY',

            # Crypto mining (additional)
            'CORZ', 'BITF',

            # Fintech
            'AFRM',

            # Quantum computing
            'RGTI',

            # Other hot small-caps
            'MULN', 'FSR', 'VFS'
        ]

        # Filter by price range
        filtered_tickers = []
        for ticker in small_cap_universe[:limit * 2]:  # Check more than needed
            try:
                price = self.get_current_price(ticker)
                if price and min_price <= price <= max_price:
                    filtered_tickers.append(ticker)

                    if len(filtered_tickers) >= limit:
                        break
            except:
                continue

        # If filtering resulted in too few, return unfiltered
        if len(filtered_tickers) < 5:
            return small_cap_universe[:limit]

        return filtered_tickers[:limit]

    def get_stock_snapshot(self, ticker: str) -> Dict:
        """
        Get complete snapshot of a stock's current state (15m, 1h, 1d multi-timeframe)

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dict with price, volume, and bar data for 15m/1h/1d
        """
        bars_dict = {}
        for interval in TIMEFRAMES:
            df = self.get_bars(ticker, interval)
            bars_dict[interval] = df.to_dict('records') if df is not None and not df.empty else []

        # Use 15m as primary for current price
        bars_15m = self.get_bars(ticker, '15m')
        bars_df = bars_15m
        if bars_df is None or bars_df.empty or len(bars_df) < 2:
            return {
                'ticker': ticker,
                'current_price': None,
                'prev_price': None,
                'current_volume': 0,
                'avg_volume': 0,
                'data_available': False,
                'bars': [],
                'bars_dict': bars_dict,
                'bars_15m': bars_dict.get('15m', []),
                'bars_1h': bars_dict.get('1h', []),
                'bars_1d': bars_dict.get('1d', []),
            }

        close_col = 'close' if 'close' in bars_df.columns else 'Close'
        if close_col not in bars_df.columns:
            return {
                'ticker': ticker,
                'current_price': None,
                'prev_price': None,
                'current_volume': 0,
                'avg_volume': 0,
                'data_available': False,
                'bars': [],
                'bars_dict': bars_dict,
                'bars_15m': bars_dict.get('15m', []),
                'bars_1h': bars_dict.get('1h', []),
                'bars_1d': bars_dict.get('1d', []),
            }
        current_price = float(bars_df.iloc[-1][close_col])
        prev_price = float(bars_df.iloc[-2][close_col])

        volume_data = self.get_volume_data(ticker)

        bars_15m_list = bars_dict.get('15m', [])
        return {
            'ticker': ticker,
            'current_price': current_price,
            'prev_price': prev_price,
            'current_volume': volume_data['current_volume'],
            'avg_volume': volume_data['avg_volume'],
            'data_available': True,
            'bars': bars_15m_list,
            'bars_dict': bars_dict,
            'bars_15m': bars_15m_list,
            'bars_1h': bars_dict.get('1h', []),
            'bars_1d': bars_dict.get('1d', []),
        }

    def get_stock_info(self, ticker: str) -> Dict:
        """
        Get additional stock information (market cap, sector, etc.)

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dict with stock info
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            return {
                'ticker': ticker,
                'company_name': info.get('longName', ticker),
                'sector': info.get('sector', 'Unknown'),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'pb_ratio': info.get('priceToBook', 0),
                'avg_volume': info.get('averageVolume', 0)
            }

        except Exception as e:
            print(f"Error fetching info for {ticker}: {str(e)}")
            return {
                'ticker': ticker,
                'company_name': ticker,
                'sector': 'Unknown',
                'market_cap': 0,
                'pe_ratio': 0,
                'pb_ratio': 0,
                'avg_volume': 0
            }


def test_data_fetcher():
    """Test data fetcher functionality"""
    print("Testing yfinance data fetcher...")

    fetcher = DataFetcher()

    # Test 1: Get current price
    print("\n1. Getting current price for AAPL...")
    price = fetcher.get_current_price('AAPL')
    print(f"   Current price: ${price:.2f}" if price else "   No data available")

    # Test 2: Get 15-min bars
    print("\n2. Getting 15-min bars for TSLA...")
    bars = fetcher.get_bars('TSLA', '15m', periods=5)
    if not bars.empty:
        print(f"   Retrieved {len(bars)} bars")
        print(f"   Latest close: ${bars.iloc[-1]['close']:.2f}")
    else:
        print("   No data available")

    # Test 3: Get stock snapshot
    print("\n3. Getting snapshot for NVDA...")
    snapshot = fetcher.get_stock_snapshot('NVDA')
    if snapshot['data_available']:
        print(f"   Current: ${snapshot['current_price']:.2f}")
        print(f"   Previous: ${snapshot['prev_price']:.2f}")
        print(f"   Volume: {snapshot['current_volume']:,.0f} (avg: {snapshot['avg_volume']:,.0f})")
    else:
        print("   No data available")

    # Test 4: Scan small caps
    print("\n4. Scanning small caps...")
    small_caps = fetcher.scan_small_caps(limit=10)
    print(f"   Found {len(small_caps)} tickers: {', '.join(small_caps[:5])}...")

    # Test 5: Get stock info
    print("\n5. Getting stock info for SOFI...")
    info = fetcher.get_stock_info('SOFI')
    print(f"   Company: {info['company_name']}")
    print(f"   Sector: {info['sector']}")
    print(f"   Market Cap: ${info['market_cap']:,.0f}")


if __name__ == '__main__':
    test_data_fetcher()
