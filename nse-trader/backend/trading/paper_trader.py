# trading/paper_trader.py
import json
import os
import sqlite3
from datetime import datetime
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.signals import generate_signals
from ai.claude_analyst import generate_daily_report

DB_PATH = "trading/paper_trades.db"
STARTING_CAPITAL = 1_000_000  # ₹10 Lakhs


def init_db():
    """Initialize SQLite database"""
    os.makedirs("trading", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS portfolio (
        id INTEGER PRIMARY KEY,
        cash REAL,
        total_value REAL,
        updated_at TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        action TEXT,
        price REAL,
        quantity INTEGER,
        value REAL,
        signal_confidence REAL,
        risk_level TEXT,
        reasoning TEXT,
        stop_loss REAL,
        target REAL,
        status TEXT DEFAULT 'OPEN',
        pnl REAL DEFAULT 0,
        created_at TEXT,
        closed_at TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS daily_summary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        portfolio_value REAL,
        daily_pnl REAL,
        daily_pnl_pct REAL,
        total_trades INTEGER,
        winning_trades INTEGER,
        report TEXT,
        created_at TEXT
    )''')

    # Initialize portfolio if empty
    c.execute("SELECT COUNT(*) FROM portfolio")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO portfolio (id, cash, total_value, updated_at) VALUES (1, ?, ?, ?)",
                  (STARTING_CAPITAL, STARTING_CAPITAL, datetime.now().isoformat()))

    conn.commit()
    conn.close()
    print("✅ Database initialized")


def get_portfolio(conn):
    c = conn.cursor()
    c.execute("SELECT cash, total_value FROM portfolio WHERE id=1")
    row = c.fetchone()
    return {'cash': row[0], 'total_value': row[1]}


def get_open_positions(conn):
    c = conn.cursor()
    c.execute("SELECT * FROM trades WHERE status='OPEN'")
    cols = [d[0] for d in c.description]
    return [dict(zip(cols, row)) for row in c.fetchall()]


def calculate_position_size(cash: float, price: float, risk_pct: float = 0.05) -> int:
    """Invest max 5% of portfolio per trade"""
    max_investment = cash * risk_pct
    quantity = int(max_investment / price)
    return max(quantity, 1)


def execute_buy(conn, signal: dict):
    """Execute a paper buy trade"""
    # Check for existing open position in same stock
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM trades WHERE symbol=? AND status='OPEN'", 
              (signal['symbol'],))
    existing = c.fetchone()[0]
    if existing > 0:
        print(f"⏭️  Skipping {signal['symbol']} — position already open")
        return None
    
    portfolio = get_portfolio(conn)
    price = signal['price']
    quantity = calculate_position_size(portfolio['cash'], price)
    value = price * quantity

    if value > portfolio['cash']:
        print(f"⚠️  Insufficient cash for {signal['symbol']}")
        return None

    stop_loss = round(price * (1 - signal['stop_loss_pct'] / 100), 2)
    target = round(price * (1 + signal['target_pct'] / 100), 2)

    c = conn.cursor()
    c.execute('''INSERT INTO trades 
        (symbol, action, price, quantity, value, signal_confidence, 
         risk_level, reasoning, stop_loss, target, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (signal['symbol'], 'BUY', price, quantity, value,
         signal['ml_confidence'], signal['risk_level'],
         signal['ai_reasoning'], stop_loss, target,
         datetime.now().isoformat()))

    new_cash = portfolio['cash'] - value
    c.execute("UPDATE portfolio SET cash=?, updated_at=? WHERE id=1",
              (new_cash, datetime.now().isoformat()))
    conn.commit()

    print(f"✅ BUY  {signal['symbol']}: {quantity} shares @ ₹{price} = ₹{value:,.0f}")
    print(f"   SL: ₹{stop_loss} | Target: ₹{target}")
    return quantity


def check_and_close_positions(conn, current_prices: dict):
    """Check if any open positions hit stop loss or target"""
    positions = get_open_positions(conn)
    c = conn.cursor()
    closed = []

    for pos in positions:
        symbol = pos['symbol']
        if symbol not in current_prices:
            continue

        current_price = current_prices[symbol]
        pnl = (current_price - pos['price']) * pos['quantity']
        pnl_pct = (current_price - pos['price']) / pos['price']

        reason = None
        if current_price <= pos['stop_loss']:
            reason = "STOP_LOSS"
        elif current_price >= pos['target']:
            reason = "TARGET_HIT"
        elif abs(pnl_pct) > 0.08:
            reason = "MAX_LOSS_EXIT"

        if reason:
            # Close position
            c.execute('''UPDATE trades SET 
                status=?, pnl=?, closed_at=?
                WHERE id=?''',
                (reason, pnl, datetime.now().isoformat(), pos['id']))

            # Return cash
            portfolio = get_portfolio(conn)
            returned = current_price * pos['quantity']
            c.execute("UPDATE portfolio SET cash=cash+?, updated_at=? WHERE id=1",
                      (returned, datetime.now().isoformat()))
            conn.commit()

            emoji = "🎯" if reason == "TARGET_HIT" else "🛑"
            print(f"{emoji} {reason}: {symbol} | P&L: ₹{pnl:+,.0f} ({pnl_pct:+.1%})")
            closed.append(pos)

    return closed


def update_portfolio_value(conn, current_prices: dict):
    """Recalculate total portfolio value"""
    portfolio = get_portfolio(conn)
    positions = get_open_positions(conn)

    holdings_value = sum(
        current_prices.get(p['symbol'], p['price']) * p['quantity']
        for p in positions
    )

    total = portfolio['cash'] + holdings_value
    c = conn.cursor()
    c.execute("UPDATE portfolio SET total_value=?, updated_at=? WHERE id=1",
              (total, datetime.now().isoformat()))
    conn.commit()
    return total


def run_daily_session():
    """Main daily trading session"""
    print(f"\n{'='*60}")
    print(f"📅 PAPER TRADING SESSION — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    conn = sqlite3.connect(DB_PATH)
    portfolio = get_portfolio(conn)

    print(f"💰 Portfolio: ₹{portfolio['total_value']:,.0f} | Cash: ₹{portfolio['cash']:,.0f}")

    # Generate signals
    signals = generate_signals(use_ai=True)
    # Log all signals to experiment tracker
    try:
        from trading.experiment_tracker import log_signals, log_market_context
        log_signals(signals, confidence_threshold=0.40)
        log_market_context(signals, 0)
    except Exception as e:
        print(f"Signal log error: {e}")
    current_prices = {s['symbol']: s['price'] for s in signals}

    # Check existing positions
    print("\n📋 Checking open positions...")
    check_and_close_positions(conn, current_prices)

    # Execute new signals
    print("\n🚀 Processing new signals...")
    trades_today = []
    for signal in signals:
        if signal['final_signal'] == 'BUY' and signal['ml_confidence'] > 0.40:
            result = execute_buy(conn, signal)
            if result:
                trades_today.append(signal)
        elif signal['final_signal'] == 'SELL':
            print(f"📉 SELL signal: {signal['symbol']} @ ₹{signal['price']} — monitor existing positions")

    # Update portfolio value
    total_value = update_portfolio_value(conn, current_prices)
    pnl = total_value - STARTING_CAPITAL
    pnl_pct = (total_value / STARTING_CAPITAL - 1)

    print(f"\n{'='*60}")
    print(f"💼 END OF SESSION SUMMARY")
    print(f"{'='*60}")
    print(f"Portfolio Value : ₹{total_value:,.0f}")
    print(f"Total P&L       : ₹{pnl:+,.0f} ({pnl_pct:+.2%})")
    print(f"Cash Available  : ₹{portfolio['cash']:,.0f}")
    print(f"Trades Today    : {len(trades_today)}")

    # Claude daily report
    if trades_today:
        print(f"\n🤖 CLAUDE'S DAILY REPORT:")
        print("-" * 40)
        report = generate_daily_report(trades_today, total_value, STARTING_CAPITAL)
        print(report)

        # Save summary
        c = conn.cursor()
        c.execute('''INSERT INTO daily_summary 
            (date, portfolio_value, daily_pnl, daily_pnl_pct, total_trades, report, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (datetime.now().strftime('%Y-%m-%d'), total_value, pnl, pnl_pct,
             len(trades_today), report, datetime.now().isoformat()))
        conn.commit()

    conn.close()
    return total_value


if __name__ == "__main__":
    init_db()
    run_daily_session()