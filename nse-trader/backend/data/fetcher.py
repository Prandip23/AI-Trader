# data/fetcher.py
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os

# Top 20 Nifty 50 stocks to start with
NIFTY_STOCKS = [
    # Financial
    "HDFCBANK.NS", "ICICIBANK.NS", "KOTAKBANK.NS", "SBIN.NS", "AXISBANK.NS",
    "BAJFINANCE.NS", "BAJAJFINSV.NS", "HDFCLIFE.NS", "SBILIFE.NS", "ICICIPRULI.NS",
    # IT
    "TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS", "LTM.NS",
    # Energy & Oil
    "RELIANCE.NS", "ONGC.NS", "BPCL.NS", "POWERGRID.NS", "NTPC.NS", "COALINDIA.NS",
    # Consumer
    "HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS", "BRITANNIA.NS", "TATACONSUM.NS",
    # Auto
    "MARUTI.NS", "TATAMOTORS.NS", "BAJAJ-AUTO.NS", "HEROMOTOCO.NS", "EICHERMOT.NS","TATAMTRDVR.NS",
    # Pharma
    "SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS",
    # Metals & Infra
    "TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS", "ULTRACEMCO.NS", "GRASIM.NS",
    # Telecom & Others
    "BHARTIARTL.NS", "ADANIENT.NS", "ADANIPORTS.NS", "LT.NS",
    # Others
    "ASIANPAINT.NS", "TITAN.NS", "INDUSINDBK.NS", "M&M.NS",
    "APOLLOHOSP.NS", "WIPRO.NS"
]

# Remove duplicates
NIFTY_STOCKS = list(dict.fromkeys(NIFTY_STOCKS))

def fetch_historical_data(symbol: str, days: int = 365) -> pd.DataFrame:
    """Fetch historical OHLCV data for a stock"""
    try:
        end = datetime.today()
        start = end - timedelta(days=days)
        
        df = yf.download(symbol, start=start, end=end, progress=False)
        
        if df.empty:
            print(f"No data found for {symbol}")
            return pd.DataFrame()
        
        # Flatten MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        df.dropna(inplace=True)
        df['Symbol'] = symbol
        
        print(f"✅ {symbol}: {len(df)} days fetched")
        return df

    except Exception as e:
        print(f"❌ Error fetching {symbol}: {e}")
        return pd.DataFrame()


def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add RSI, MACD, Bollinger Bands, moving averages"""
    if df.empty or len(df) < 26:
        return df

    close = df['Close']

    # Moving Averages
    df['SMA_20'] = close.rolling(window=20).mean()
    df['SMA_50'] = close.rolling(window=50).mean()
    df['EMA_12'] = close.ewm(span=12, adjust=False).mean()
    df['EMA_26'] = close.ewm(span=26, adjust=False).mean()

    # MACD
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']

    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # Bollinger Bands
    df['BB_Mid'] = close.rolling(window=20).mean()
    bb_std = close.rolling(window=20).std()
    df['BB_Upper'] = df['BB_Mid'] + (2 * bb_std)
    df['BB_Lower'] = df['BB_Mid'] - (2 * bb_std)
    df['BB_Width'] = df['BB_Upper'] - df['BB_Lower']

    # Volume MA
    df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
    df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']

    # Price change features
    df['Return_1d'] = close.pct_change(1)
    df['Return_5d'] = close.pct_change(5)
    df['Return_10d'] = close.pct_change(10)

    df.dropna(inplace=True)
    return df


def fetch_all_stocks(days: int = 365) -> dict:
    """Fetch and process all Nifty stocks"""
    all_data = {}
    print(f"\n📥 Fetching data for {len(NIFTY_STOCKS)} stocks...\n")
    
    for symbol in NIFTY_STOCKS:
        df = fetch_historical_data(symbol, days)
        if not df.empty:
            df = add_technical_indicators(df)
            if not df.empty:
                all_data[symbol] = df

    print(f"\n✅ Successfully fetched {len(all_data)} stocks\n")
    return all_data


if __name__ == "__main__":
    # Test the fetcher
    data = fetch_all_stocks(days=365)
    for symbol, df in list(data.items())[:2]:
        print(f"\n{symbol}:")
        print(df.tail(3))
        print(f"Columns: {list(df.columns)}")