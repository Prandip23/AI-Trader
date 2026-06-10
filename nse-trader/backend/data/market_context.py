# data/market_context.py
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta


def get_vix() -> dict:
    """Fetch India VIX"""
    try:
        vix = yf.download("^INDIAVIX", period="5d", progress=False)

        if isinstance(vix.columns, pd.MultiIndex):
            vix.columns = vix.columns.get_level_values(0)

        if vix.empty:
            print("⚠️ VIX data unavailable, using default")
            return {"vix": 15.0, "vix_signal": "NORMAL", "vix_change": 0}

        latest_vix = float(vix['Close'].iloc[-1])
        prev_vix = float(vix['Close'].iloc[-2]) if len(vix) > 1 else latest_vix
        vix_change = round((latest_vix - prev_vix) / prev_vix * 100, 2)

        if latest_vix < 15:
            vix_signal = "LOW_FEAR"
        elif latest_vix < 20:
            vix_signal = "NORMAL"
        elif latest_vix < 25:
            vix_signal = "CAUTION"
        else:
            vix_signal = "HIGH_FEAR"

        return {
            "vix": round(latest_vix, 2),
            "vix_signal": vix_signal,
            "vix_change": vix_change
        }

    except Exception as e:
        print(f"VIX fetch error: {e}")
        return {"vix": 15.0, "vix_signal": "NORMAL", "vix_change": 0}


def get_nifty_trend() -> dict:
    """Check if Nifty is in uptrend or downtrend"""
    try:
        nifty = yf.download("^NSEI", period="60d", progress=False)

        if isinstance(nifty.columns, pd.MultiIndex):
            nifty.columns = nifty.columns.get_level_values(0)

        if nifty.empty:
            return {"nifty_close": 0, "nifty_trend": "NEUTRAL",
                    "nifty_vs_sma20": 0, "nifty_vs_sma50": 0,
                    "nifty_change_1d": 0, "nifty_change_5d": 0}

        close = nifty['Close']
        latest = float(close.iloc[-1])
        sma20 = float(close.rolling(20).mean().iloc[-1])
        sma50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else sma20
        change_1d = float((close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100)
        change_5d = float((close.iloc[-1] - close.iloc[-6]) / close.iloc[-6] * 100) if len(close) >= 6 else 0

        vs_sma20 = round((latest - sma20) / sma20 * 100, 2)
        vs_sma50 = round((latest - sma50) / sma50 * 100, 2)

        if latest > sma20 and latest > sma50:
            trend = "BULLISH"
        elif latest < sma20 and latest < sma50:
            trend = "BEARISH"
        else:
            trend = "NEUTRAL"

        return {
            "nifty_close": round(latest, 2),
            "nifty_trend": trend,
            "nifty_vs_sma20": vs_sma20,
            "nifty_vs_sma50": vs_sma50,
            "nifty_change_1d": round(change_1d, 2),
            "nifty_change_5d": round(change_5d, 2)
        }

    except Exception as e:
        print(f"Nifty trend error: {e}")
        return {"nifty_close": 0, "nifty_trend": "NEUTRAL",
                "nifty_vs_sma20": 0, "nifty_vs_sma50": 0,
                "nifty_change_1d": 0, "nifty_change_5d": 0}


def get_market_breadth(all_stock_data: dict) -> dict:
    """
    Calculate what % of Nifty stocks are bullish
    Bullish = price above SMA20
    """
    if not all_stock_data:
        return {"breadth_pct": 50, "breadth_signal": "NEUTRAL",
                "bullish_count": 0, "bearish_count": 0}

    bullish = 0
    bearish = 0

    for symbol, df in all_stock_data.items():
        if df.empty or 'Close' not in df.columns or 'SMA_20' not in df.columns:
            continue
        latest = df.iloc[-1]
        if float(latest['Close']) > float(latest['SMA_20']):
            bullish += 1
        else:
            bearish += 1

    total = bullish + bearish
    breadth_pct = round(bullish / total * 100, 1) if total > 0 else 50

    if breadth_pct >= 60:
        breadth_signal = "BULLISH"
    elif breadth_pct >= 40:
        breadth_signal = "NEUTRAL"
    else:
        breadth_signal = "BEARISH"

    return {
        "breadth_pct": breadth_pct,
        "breadth_signal": breadth_signal,
        "bullish_count": bullish,
        "bearish_count": bearish
    }


def get_full_market_context(all_stock_data: dict = None) -> dict:
    """Get complete market context — VIX + Nifty + Breadth"""
    print("\n🌍 Fetching market context...")

    vix_data = get_vix()
    nifty_data = get_nifty_trend()
    breadth_data = get_market_breadth(all_stock_data or {})

    # Overall market verdict
    score = 0

    # VIX scoring
    if vix_data['vix_signal'] == 'LOW_FEAR':
        score += 2
    elif vix_data['vix_signal'] == 'NORMAL':
        score += 1
    elif vix_data['vix_signal'] == 'CAUTION':
        score -= 1
    elif vix_data['vix_signal'] == 'HIGH_FEAR':
        score -= 3

    # Nifty trend scoring
    if nifty_data['nifty_trend'] == 'BULLISH':
        score += 2
    elif nifty_data['nifty_trend'] == 'NEUTRAL':
        score += 0
    elif nifty_data['nifty_trend'] == 'BEARISH':
        score -= 2

    # Breadth scoring
    if breadth_data['breadth_signal'] == 'BULLISH':
        score += 1
    elif breadth_data['breadth_signal'] == 'BEARISH':
        score -= 1

    # Final verdict
    if score >= 3:
        market_verdict = "STRONG_BUY"
        max_positions = 8
        position_size_multiplier = 1.0
    elif score >= 1:
        market_verdict = "CAUTIOUS_BUY"
        max_positions = 5
        position_size_multiplier = 0.75
    elif score == 0:
        market_verdict = "NEUTRAL"
        max_positions = 3
        position_size_multiplier = 0.5
    elif score >= -2:
        market_verdict = "AVOID_BUY"
        max_positions = 0
        position_size_multiplier = 0.0
    else:
        market_verdict = "STRONG_AVOID"
        max_positions = 0
        position_size_multiplier = 0.0

    context = {
        **vix_data,
        **nifty_data,
        **breadth_data,
        "market_score": score,
        "market_verdict": market_verdict,
        "max_positions": max_positions,
        "position_size_multiplier": position_size_multiplier
    }

    print(f"📊 VIX: {vix_data['vix']} ({vix_data['vix_signal']})")
    print(f"📈 Nifty: {nifty_data['nifty_close']} ({nifty_data['nifty_trend']}) | 1d: {nifty_data['nifty_change_1d']}%")
    print(f"🌡️  Breadth: {breadth_data['breadth_pct']}% bullish ({breadth_data['breadth_signal']})")
    print(f"🎯 Market Verdict: {market_verdict} (score: {score})")

    return context


if __name__ == "__main__":
    context = get_full_market_context()
    print("\n✅ Full Market Context:")
    for k, v in context.items():
        print(f"  {k}: {v}")