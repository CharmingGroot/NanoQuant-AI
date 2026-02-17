"""
core/data_fetcher.py - Market data fetcher using yfinance (free, no API key needed)
"""

import os
import sys

from util.platform import fix_windows_ssl
fix_windows_ssl()

import yfinance as yf
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import pandas as pd

INTERVAL_CONFIG: Dict[str, Tuple[int, Optional[int], Optional[str]]] = {
    '15m': (40, 7, None),
    '1h': (40, 60, None),
    '1d': (30, None, '2mo'),
}
TIMEFRAMES = list(INTERVAL_CONFIG.keys())

# 섹터별 소형주 유니버스 (Russell 2000 중심, GICS 기준 ~100개씩)
SECTOR_UNIVERSE: Dict[str, List[str]] = {
    "Technology": [
        "SOFI", "HOOD", "COIN", "PLTR", "RBLX", "DASH", "UPST", "OPEN", "AFRM", "NU",
        "MSTR", "SMCI", "SOUN", "BBAI", "IONQ", "QUBT", "RKLB", "ASTS", "RGTI", "AEHR",
        "NVTS", "RDW", "ASTR", "SPIR", "BBAI", "PRCH", "AI", "PATH", "DOCN", "FROG",
        "CFLT", "GTLB", "NET", "DDOG", "MDB", "SNOW", "CRWD", "ZS", "OKTA", "TWLO",
        "BILL", "HUBS", "ZM", "DOCU", "TEAM", "WDAY", "VEEV", "ANSS", "CDNS", "SNPS",
        "MRVL", "AMD", "AVGO", "LRCX", "AMAT", "KLAC", "ENTG", "MKSI", "POWI", "SYNA",
        "RMBS", "SWKS", "QRVO", "MPWR", "ON", "NXPI", "MCHP", "ADI", "TXN", "MU",
        "WDC", "STX", "MXL", "SMTC", "CRUS", "ALGM", "WOLF", "SLAB", "AEHR",
        "COHR", "HIMX", "PXLW", "CREE", "IIVI", "LITE", "FNSR", "ACIA", "LITE",
        "INFN", "NEON", "CAMT", "PRGS", "MANH", "FTNT", "CHKP", "CYBR", "PANW",
    ],
    "Healthcare": [
        "VKTX", "OCEA", "JANX", "LBPH", "RNA", "SRNE", "MRNA", "BNTX", "NVAX", "INMB",
        "VRTX", "REGN", "BIIB", "GILD", "AMGN", "ILMN", "DXCM", "ALGN", "HZNP", "SGEN",
        "EXEL", "JAZZ", "INCY", "ALKS", "SRPT", "BMRN", "NBIX", "UTHR", "HOLX", "IDXX",
        "TECH", "ICLR", "CRL", "MEDP", "PODD", "RMD", "ZBH", "BAX", "BSX", "EW",
        "SYK", "ABT", "JNJ", "MDT", "ISRG", "SMA", "HCA", "MOH", "CNC", "EHC",
        "OSCR", "HIMS", "TDOC", "AMWL", "LFST", "DOCS", "GH", "SEM", "ACHC", "CYH",
        "THC", "HCA", "UHS", "CHE", "DVA", "FMS", "BKD", "ENSG", "AMED", "LHCG",
        "ADUS", "HCAT", "OPCH", "AVNS", "PDCO", "HSIC", "DENT", "XRAY", "ABMD",
        "ALGN", "NVST", "COO", "RMD", "ZBH", "BSX", "EW", "SYK", "BAX", "BDX",
        "TNDM", "DXCM", "PODD", "IDXX", "HOLX", "A", "TMO", "DHR", "WAT", "WST",
    ],
    "Financials": [
        "SOFI", "UPST", "AFRM", "LC", "OPEN", "LDI", "RKT", "UWMC", "COIN", "HOOD",
        "MSTR", "RIOT", "MARA", "BTBT", "HUT", "CLSK", "CIFR", "CORZ", "HIVE",
        "SI", "VLY", "WSFS", "PB", "WTFC", "FULT", "FHN", "KEY", "CFG", "FNB",
        "PNC", "TFC", "USB", "FITB", "HBAN", "MTB", "ZION", "RF", "CMA", "CFR",
        "EWBC", "PACW", "WAL", "FRC", "SIVB", "FRC", "NYCB", "NYCB", "FFWM",
        "BANC", "PPBI", "CVBF", "HOPE", "FFIC", "FBP", "BPOP", "BOH", "CBU",
        "IBOC", "TCBI", "WABC", "SBNY", "SIVB", "FNF", "RDN", "MTG", "ESNT",
        "NMIH", "ACT", "AGNC", "NLY", "ARR", "TWO", "RWT", "LADR", "RC", "BXMT",
        "TRTX", "STWD", "CLNY", "AIV", "UDR", "AVB", "EQR", "ESS", "MAA", "UDR",
        "CACC", "NAVI", "OPFI", "LC", "SOFI", "UPST", "AFRM", "OPEN", "RKT",
    ],
    "Industrials": [
        "RKLB", "RKT", "SPCE", "LUNR", "RDW", "ASTR", "RGTI", "ASTS", "SATL",
        "DECK", "CROX", "WWW", "SHOO", "BOOT", "SCVL", "CAL", "HIBB", "FL",
        "W", "CHWY", "RH", "WSM", "LZB", "ETH", "LCII", "LOVE", "PRPL", "TPX",
        "LII", "CARR", "JCI", "LEN", "DHI", "NVR", "PHM", "TOL", "MHO", "CVCO",
        "MHO", "MTH", "KBH", "LGIH", "SKY", "CCS", "BZH", "DFH", "GRBK",
        "EME", "PWR", "J", "FLR", "PJT", "GSHD", "MMS", "VRSK", "FISV",
        "CACI", "LDOS", "HII", "NOC", "LMT", "RTX", "GD", "LHX", "TXT",
        "JOBY", "LILM", "EVTL", "ACHR", "EH", "GOGO", "VLRS", "ALGT",
        "SAIA", "XPO", "ODFL", "JBHT", "CHRW", "RXO", "KNX", "WERN", "HTLD",
        "ARCB", "USX", "PTSI", "CVLG", "DDS", "GEO", "CXW", "SFL", "SSW",
    ],
    "Consumer Discretionary": [
        "PTON", "W", "CHWY", "RH", "WSM", "LZB", "DKS", "BGFV", "ASO", "HIBB",
        "BOOT", "SCVL", "CAL", "BKE", "PLCE", "ZUMZ", "CONN", "BBY", "GME", "AMC",
        "BBBY", "WISH", "W", "CHWY", "ETSY", "EBAY", "WMT", "TGT", "COST",
        "LCID", "RIVN", "XPEV", "LI", "NIO", "FSR", "NKLA", "GOEV", "RIDE",
        "F", "GM", "FCAU", "TSLA", "RIVN", "LCID", "NIO", "XPEV", "LI",
        "AN", "KMX", "LAD", "SAH", "ABG", "CARS", "CVNA", "VRM", "LOT",
        "DHI", "LEN", "NVR", "PHM", "TOL", "KBH", "MHO", "LGIH", "DFH",
        "MGM", "WYNN", "LVS", "PENN", "CZR", "BALY", "BYD", "RRR", "PLAY",
        "FUN", "SIX", "MTN", "SKIS", "LUV", "UAL", "DAL", "ALK",
        "CCL", "NCLH", "RCL", "LIND", "NCLH", "SBLK", "EGLE", "GOGL", "SALT",
    ],
    "Energy": [
        "MARA", "RIOT", "BTBT", "HUT", "CLSK", "CIFR", "HIVE", "CORZ", "BITF",
        "OXY", "DVN", "FANG", "MRO", "HES", "COP", "EOG", "PXD", "EQT", "RRC",
        "SWN", "AR", "CHRD", "MTDR", "SM", "MGY", "CRGY", "VTLE", "PR", "CPE",
        "GTE", "REI", "WLL", "LPI", "PDCE", "PE", "WRD", "VOC", "MUR", "FANG",
        "HP", "PTEN", "NBR", "RIG", "VAL", "TDW", "DO", "BORR", "SDRL", "BWO",
        "NOV", "SLB", "HAL", "BKR", "CHX", "HP", "PTEN", "NBR", "RIG",
        "LNG", "CQP", "TELL", "NEXT", "GLNG",
        "PBF", "VLO", "MPC", "PSX", "HFC", "DK", "PARR", "CLMT", "CVI",
        "OMP", "ET", "EPD", "KMI", "PAA", "MPLX", "WES", "HESM", "ET",
        "DVN", "FANG", "MRO", "HES", "COP", "OXY", "EOG", "PXD", "EQT",
    ],
    "Materials": [
        "FCX", "NEM", "NUE", "STLD", "RS", "CLF", "ATI", "CMC", "X", "AA",
        "ALB", "LTHM", "LAC", "SQM", "LITM", "PLL", "LAC", "LI", "MP",
        "CE", "EMN", "LYB", "WLK", "HUN", "OLN", "FUL", "KWR", "SHW", "PPG",
        "CC", "SCL", "WRK", "IP", "PKG", "SEE", "AMCR", "SON", "BERY",
        "SMG", "CF", "MOS", "NTR", "FMC", "CTVA", "CBT", "AXTA", "HUN",
        "IFF", "RPM", "EMN", "CE", "WLK", "HUN", "OLN", "FUL", "KWR",
        "FCX", "TECK", "SCCO", "CLF", "X", "STLD", "RS", "CMC", "NUE", "ATI",
        "FMC", "CTVA", "NTR", "CF", "MOS", "CBT", "AXTA", "IFF", "RPM",
        "GOLD", "KGC", "AEM", "EGO", "CDE", "PAAS", "HL", "AG", "MUX",
        "LAC", "ALB", "SQM", "LTHM", "MP", "PLL", "LITM", "LAC", "LAC",
    ],
}


def _flatten_sector_universe(per_sector: int = 100) -> List[str]:
    """섹터별 per_sector개씩 포함한 플랫 유니버스 반환."""
    out: List[str] = []
    seen: set = set()
    for tickers in SECTOR_UNIVERSE.values():
        for t in tickers[:per_sector]:
            t = str(t).strip().upper()
            if t and t not in seen:
                seen.add(t)
                out.append(t)
    return out


class DataFetcher:
    def __init__(self):
        pass

    def get_bars(self, ticker: str, interval: str, periods: int = None) -> pd.DataFrame:
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
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period='1d', interval='1m')
            if data is None or not isinstance(data, pd.DataFrame) or data.empty:
                return None
            close_col = 'Close' if 'Close' in data.columns else 'close'
            if close_col not in data.columns:
                return None
            return float(data[close_col].iloc[-1])
        except Exception as e:
            print(f"Error fetching current price for {ticker}: {str(e)}")
            return None

    def get_volume_data(self, ticker: str, current_period_minutes: int = 15) -> Dict[str, float]:
        bars_df = self.get_bars(ticker, '15m', periods=5 * 24 * 4)
        if bars_df is None or bars_df.empty:
            return {'current_volume': 0, 'avg_volume': 0}
        vol_col = 'volume' if 'volume' in bars_df.columns else 'Volume'
        if vol_col not in bars_df.columns:
            return {'current_volume': 0, 'avg_volume': 0}
        current_volume = float(bars_df.iloc[-1][vol_col]) if len(bars_df) > 0 else 0
        avg_volume = float(bars_df.iloc[:-1][vol_col].mean()) if len(bars_df) > 1 else current_volume
        return {'current_volume': current_volume, 'avg_volume': avg_volume}

    def scan_small_caps(self, min_price: float = 1.0, max_price: float = 50.0, limit: int = 100) -> List[str]:
        universe = self.get_ticker_universe()
        if not universe:
            universe = self._default_small_cap_universe()
        filtered_tickers = []
        max_scan = min(len(universe), int(os.environ.get('SCAN_UNIVERSE_CAP', 1500)))
        for ticker in universe[:max_scan]:
            try:
                price = self.get_current_price(ticker)
                if price and min_price <= price <= max_price:
                    filtered_tickers.append(ticker)
                    if len(filtered_tickers) >= limit:
                        break
            except:
                continue
        if len(filtered_tickers) < 5:
            return universe[:limit]
        return filtered_tickers[:limit]

    def get_ticker_universe(self) -> List[str]:
        try:
            from forecast import load_watchlist
            tickers = load_watchlist()
            return list(tickers) if tickers else []
        except Exception:
            return []

    def _default_small_cap_universe(self) -> List[str]:
        per_sector = int(os.environ.get('SECTOR_TICKERS_LIMIT', 100))
        return _flatten_sector_universe(per_sector=per_sector)

    def get_stock_snapshot(self, ticker: str) -> Dict:
        bars_dict = {}
        for interval in TIMEFRAMES:
            df = self.get_bars(ticker, interval)
            bars_dict[interval] = df.to_dict('records') if df is not None and not df.empty else []
        bars_15m = self.get_bars(ticker, '15m')
        bars_df = bars_15m
        if bars_df is None or bars_df.empty or len(bars_df) < 2:
            return {
                'ticker': ticker, 'current_price': None, 'prev_price': None,
                'current_volume': 0, 'avg_volume': 0, 'data_available': False,
                'bars': [], 'bars_dict': bars_dict,
                'bars_15m': bars_dict.get('15m', []), 'bars_1h': bars_dict.get('1h', []), 'bars_1d': bars_dict.get('1d', []),
            }
        close_col = 'close' if 'close' in bars_df.columns else 'Close'
        if close_col not in bars_df.columns:
            return {
                'ticker': ticker, 'current_price': None, 'prev_price': None,
                'current_volume': 0, 'avg_volume': 0, 'data_available': False,
                'bars': [], 'bars_dict': bars_dict,
                'bars_15m': bars_dict.get('15m', []), 'bars_1h': bars_dict.get('1h', []), 'bars_1d': bars_dict.get('1d', []),
            }
        current_price = float(bars_df.iloc[-1][close_col])
        prev_price = float(bars_df.iloc[-2][close_col])
        volume_data = self.get_volume_data(ticker)
        bars_15m_list = bars_dict.get('15m', [])
        return {
            'ticker': ticker, 'current_price': current_price, 'prev_price': prev_price,
            'current_volume': volume_data['current_volume'], 'avg_volume': volume_data['avg_volume'],
            'data_available': True, 'bars': bars_15m_list, 'bars_dict': bars_dict,
            'bars_15m': bars_15m_list, 'bars_1h': bars_dict.get('1h', []), 'bars_1d': bars_dict.get('1d', []),
        }

    def get_stock_info(self, ticker: str) -> Dict:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            return {
                'ticker': ticker, 'company_name': info.get('longName', ticker),
                'sector': info.get('sector', 'Unknown'), 'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', 0), 'pb_ratio': info.get('priceToBook', 0),
                'avg_volume': info.get('averageVolume', 0)
            }
        except Exception as e:
            print(f"Error fetching info for {ticker}: {str(e)}")
            return {
                'ticker': ticker, 'company_name': ticker, 'sector': 'Unknown',
                'market_cap': 0, 'pe_ratio': 0, 'pb_ratio': 0, 'avg_volume': 0
            }
