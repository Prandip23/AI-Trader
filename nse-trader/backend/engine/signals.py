# engine/signals.py
import pandas as pd
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.fetcher import fetch_all_stocks, NIFTY_STOCKS
from models.trainer import load_model, FEATURE_COLUMNS
from ai.claude_analyst import analyse_signal
from data.market_context import get_full_market_context

LABEL_MAP = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}


def get_latest_indicators(df: pd.DataFrame) -> dict:
    latest = df.iloc[-1]
    close = latest['Close']
    return {
        'RSI': float(latest['RSI']),
        'MACD': float(latest['MACD']),
        'MACD_Signal': float(latest['MACD_Signal']),
        'Volume_Ratio': float(latest['Volume_Ratio']),
        'price_vs_sma20': float((close - latest['SMA_20']) / latest['SMA_20']),
        'price_vs_sma50': float((close - latest['SMA_50']) / latest['SMA_50']),
        'bb_position': float((close - latest['BB_Lower']) / latest['BB_Width'])
                       if latest['BB_Width'] > 0 else 0.5,
    }


def generate_signals(use_ai: bool = True) -> list:
    """Generate trading signals with market context filter"""
    print("\n🔍 Generating signals...\n")

    try:
        model, scaler = load_model()
    except FileNotFoundError:
        print("❌ No model found. Run trainer.py first.")
        return []

    # Fetch all stock data
    all_data = fetch_all_stocks(days=365)

    # Get market context — VIX + Nifty + Breadth
    market_ctx = get_full_market_context(all_data)

    # Block all buys if market is too risky
    block_buys = market_ctx['market_verdict'] in ['AVOID_BUY', 'STRONG_AVOID']
    if block_buys:
        print(f"\n🚫 BUY signals BLOCKED — Market verdict: {market_ctx['market_verdict']}")
        print(f"   VIX: {market_ctx['vix']} | Nifty: {market_ctx['nifty_trend']} | Breadth: {market_ctx['breadth_pct']}%\n")

    signals = []

    for symbol, df in all_data.items():
        try:
            latest = df.iloc[-1]
            features = df[FEATURE_COLUMNS].iloc[-1:].copy()

            if features.isnull().any().any():
                continue

            features_scaled = scaler.transform(features)
            prediction = model.predict(features_scaled)[0]
            probabilities = model.predict_proba(features_scaled)[0]
            confidence = float(max(probabilities))
            ml_signal = LABEL_MAP[prediction]

            if ml_signal == 'HOLD' and confidence < 0.75:
                continue

            # Block BUY if market conditions are bad
            if ml_signal == 'BUY' and block_buys:
                ml_signal = 'HOLD'

            signal_data = {
                'symbol': symbol,
                'price': round(float(latest['Close']), 2),
                'ml_signal': ml_signal,
                'ml_confidence': round(confidence, 3),
                'rsi': round(float(latest['RSI']), 1),
                'macd': round(float(latest['MACD']), 4),
                'macd_signal': round(float(latest['MACD_Signal']), 4),
                'volume_ratio': round(float(latest['Volume_Ratio']), 2),
                'return_1d': round(float(latest['Return_1d']), 4),
                'return_5d': round(float(latest['Return_5d']), 4),
                # Market context attached to every signal
                'market_verdict': market_ctx['market_verdict'],
                'vix': market_ctx['vix'],
                'vix_signal': market_ctx['vix_signal'],
                'nifty_trend': market_ctx['nifty_trend'],
                'breadth_pct': market_ctx['breadth_pct'],
                'position_size_multiplier': market_ctx['position_size_multiplier'],
            }

            # Claude AI validation
            if use_ai and ml_signal in ['BUY', 'SELL']:
                print(f"🤖 Claude analysing {symbol}...")
                indicators = get_latest_indicators(df)

                # Pass market context to Claude
                indicators['vix'] = market_ctx['vix']
                indicators['vix_signal'] = market_ctx['vix_signal']
                indicators['nifty_trend'] = market_ctx['nifty_trend']
                indicators['market_breadth'] = market_ctx['breadth_pct']

                # Fetch news
                try:
                    from data.news_fetcher import fetch_stock_news, format_news_for_claude
                    news_items = fetch_stock_news(symbol, max_articles=5)
                    news_text = format_news_for_claude(symbol, news_items)
                    signal_data['news_headlines'] = [n['title'] for n in news_items]
                    print(f"   📰 {len(news_items)} news articles found")
                except Exception as e:
                    news_text = ""
                    signal_data['news_headlines'] = []

                ai_result = analyse_signal(
                    symbol, ml_signal, confidence, indicators, news_text
                )

                signal_data['ai_signal'] = ai_result.get('validated_signal', ml_signal)
                signal_data['ai_reasoning'] = ai_result.get('reasoning', '')
                signal_data['risk_level'] = ai_result.get('risk_level', 'MEDIUM')
                signal_data['stop_loss_pct'] = ai_result.get('suggested_stop_loss_pct', 2.5)
                signal_data['target_pct'] = ai_result.get('suggested_target_pct', 5.0)
                signal_data['key_concern'] = ai_result.get('key_concern', '')
                signal_data['news_sentiment'] = ai_result.get('news_sentiment', 'NO_NEWS')
                signal_data['final_signal'] = signal_data['ai_signal']
            else:
                signal_data['final_signal'] = ml_signal
                signal_data['ai_signal'] = ml_signal
                signal_data['ai_reasoning'] = 'AI validation skipped'
                signal_data['risk_level'] = 'MEDIUM'
                signal_data['stop_loss_pct'] = 2.5
                signal_data['target_pct'] = 5.0
                signal_data['key_concern'] = ''

            signals.append(signal_data)

        except Exception as e:
            print(f"❌ Error processing {symbol}: {e}")
            continue

    signals.sort(key=lambda x: (x['final_signal'] != 'HOLD', x['ml_confidence']), reverse=True)
    print(f"\n✅ Generated {len(signals)} signals")
    print(f"📊 Market: {market_ctx['market_verdict']} | VIX: {market_ctx['vix']} | Breadth: {market_ctx['breadth_pct']}%")
    return signals


if __name__ == "__main__":
    signals = generate_signals(use_ai=True)
    print("\n📊 TODAY'S SIGNALS:")
    print("-" * 60)
    for s in signals:
        if s['final_signal'] in ['BUY', 'SELL']:
            print(f"\n{s['symbol']}: {s['final_signal']} @ ₹{s['price']}")
            print(f"  Confidence: {s['ml_confidence']:.1%} | Risk: {s['risk_level']}")
            print(f"  Market: {s['market_verdict']} | VIX: {s['vix']} | Breadth: {s['breadth_pct']}%")
            print(f"  AI: {s['ai_reasoning']}")