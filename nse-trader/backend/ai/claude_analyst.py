# ai/claude_analyst.py
import anthropic
import os
from dotenv import load_dotenv
import json

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Track prompt version for experiment logging
PROMPT_VERSION = "v3_with_news"


def analyse_signal(symbol: str, signal: str, confidence: float,
                   indicators: dict, news_text: str = "") -> dict:
    """Send signal to Claude for validation with news context"""

    news_section = f"""
Recent News:
{news_text if news_text else "No recent news available."}
""" if news_text else ""

    prompt = f"""
You are an expert NSE India stock market analyst.
Analyze this trading signal and provide your assessment.

Stock: {symbol}
ML Model Signal: {signal}
Model Confidence: {confidence:.1%}

Current Technical Indicators:
- RSI: {indicators.get('RSI', 'N/A'):.1f}
- MACD: {indicators.get('MACD', 'N/A'):.4f}
- MACD Signal: {indicators.get('MACD_Signal', 'N/A'):.4f}
- Price vs SMA20: {indicators.get('price_vs_sma20', 'N/A'):.2%}
- Price vs SMA50: {indicators.get('price_vs_sma50', 'N/A'):.2%}
- Volume Ratio: {indicators.get('Volume_Ratio', 'N/A'):.2f}x average
- BB Position: {indicators.get('bb_position', 'N/A'):.2%} of band width

Market Context:
- India VIX: {indicators.get('vix', 'N/A')} ({indicators.get('vix_signal', 'N/A')})
- Nifty Trend: {indicators.get('nifty_trend', 'N/A')}
- Market Breadth: {indicators.get('market_breadth', 'N/A')}% stocks above SMA20
{news_section}
Important: This is a paper trading system for learning. Be moderately bullish -
only override ML signal to HOLD if there are STRONG contradicting signals.
Low volume alone is not sufficient reason to override a BUY signal.
However, if news contains earnings miss, scandal, regulatory action or major
negative event — downgrade signal to HOLD or SELL regardless of technicals.
If news contains earnings beat, major contract win, or strong positive catalyst
— upgrade confidence and consider upgrading HOLD to BUY.

Respond ONLY with a JSON object, no markdown, no explanation outside JSON:
{{
    "validated_signal": "BUY or SELL or HOLD",
    "confidence_adjustment": "higher or same or lower",
    "reasoning": "2-3 sentence explanation including news impact if relevant",
    "risk_level": "LOW or MEDIUM or HIGH",
    "suggested_stop_loss_pct": 2.5,
    "suggested_target_pct": 5.0,
    "key_concern": "one main risk to watch",
    "news_sentiment": "POSITIVE or NEUTRAL or NEGATIVE or NO_NEWS"
}}
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = response.content[0].text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)
        return result

    except Exception as e:
        print(f"Claude API error for {symbol}: {e}")
        return {
            "validated_signal": signal,
            "confidence_adjustment": "same",
            "reasoning": "AI analysis unavailable, using ML signal directly.",
            "risk_level": "MEDIUM",
            "suggested_stop_loss_pct": 2.5,
            "suggested_target_pct": 5.0,
            "key_concern": "No AI validation available",
            "news_sentiment": "NO_NEWS"
        }


def generate_daily_report(trades: list, portfolio_value: float,
                          starting_value: float,
                          market_context: dict = None) -> str:
    """Claude generates end of day summary with market context"""

    market_section = ""
    if market_context:
        market_section = f"""
Market Conditions:
- India VIX: {market_context.get('vix', 'N/A')} ({market_context.get('vix_signal', 'N/A')})
- Nifty Trend: {market_context.get('nifty_trend', 'N/A')}
- Market Breadth: {market_context.get('breadth_pct', 'N/A')}% stocks bullish
- Market Verdict: {market_context.get('market_verdict', 'N/A')}
"""

    prompt = f"""
You are an expert trading coach reviewing a paper trading session on NSE India.

Portfolio Summary:
- Starting Value: ₹{starting_value:,.0f}
- Current Value: ₹{portfolio_value:,.0f}
- P&L: ₹{portfolio_value - starting_value:,.0f} ({((portfolio_value/starting_value)-1):.2%})
{market_section}
Today's Trades:
{json.dumps(trades, indent=2)}

Write a concise daily report (5-7 lines) covering:
1. Overall performance and market conditions
2. Best and worst calls with news context if relevant
3. What the model got right
4. What to watch tomorrow
Keep it practical and specific to NSE India market conditions.
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()

    except Exception as e:
        return f"Daily report unavailable: {e}"