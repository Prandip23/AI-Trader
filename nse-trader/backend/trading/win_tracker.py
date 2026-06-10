# trading/win_tracker.py
import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = "trading/paper_trades.db"


def get_win_rate_stats(days: int = 30) -> dict:
    """Calculate win rate and performance stats for last N days"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    since = (datetime.now() - timedelta(days=days)).isoformat()

    # Get all closed trades
    c.execute('''SELECT symbol, action, price, quantity, value, 
                 pnl, status, signal_confidence, risk_level, created_at
                 FROM trades 
                 WHERE status != 'OPEN' AND created_at > ?
                 ORDER BY created_at DESC''', (since,))
    cols = [d[0] for d in c.description]
    closed_trades = [dict(zip(cols, row)) for row in c.fetchall()]

    # Get all open trades
    c.execute('''SELECT symbol, action, price, quantity, value,
                 signal_confidence, risk_level, created_at
                 FROM trades WHERE status = 'OPEN' AND created_at > ?''', (since,))
    cols = [d[0] for d in c.description]
    open_trades = [dict(zip(cols, row)) for row in c.fetchall()]

    conn.close()

    if not closed_trades:
        return {
            "period_days": days,
            "total_closed": 0,
            "total_open": len(open_trades),
            "wins": 0,
            "losses": 0,
            "win_rate": 0,
            "total_pnl": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "best_trade": None,
            "worst_trade": None,
            "risk_reward_ratio": 0,
            "profit_factor": 0,
            "by_stock": [],
            "by_confidence": [],
            "monthly_summary": []
        }

    # Core stats
    wins = [t for t in closed_trades if t['pnl'] > 0]
    losses = [t for t in closed_trades if t['pnl'] <= 0]
    total_pnl = sum(t['pnl'] for t in closed_trades)
    avg_win = sum(t['pnl'] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t['pnl'] for t in losses) / len(losses) if losses else 0
    win_rate = len(wins) / len(closed_trades) * 100 if closed_trades else 0

    # Best and worst
    best = max(closed_trades, key=lambda x: x['pnl']) if closed_trades else None
    worst = min(closed_trades, key=lambda x: x['pnl']) if closed_trades else None

    # Risk/Reward
    gross_profit = sum(t['pnl'] for t in wins) if wins else 0
    gross_loss = abs(sum(t['pnl'] for t in losses)) if losses else 1
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 0

    rr_ratio = round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else 0

    # By stock performance
    stock_perf = {}
    for t in closed_trades:
        sym = t['symbol'].replace('.NS', '')
        if sym not in stock_perf:
            stock_perf[sym] = {'symbol': sym, 'trades': 0, 'wins': 0, 'pnl': 0}
        stock_perf[sym]['trades'] += 1
        stock_perf[sym]['pnl'] += t['pnl']
        if t['pnl'] > 0:
            stock_perf[sym]['wins'] += 1

    for sym in stock_perf:
        t = stock_perf[sym]['trades']
        w = stock_perf[sym]['wins']
        stock_perf[sym]['win_rate'] = round(w / t * 100, 1) if t > 0 else 0
        stock_perf[sym]['pnl'] = round(stock_perf[sym]['pnl'], 2)

    by_stock = sorted(stock_perf.values(), key=lambda x: x['pnl'], reverse=True)

    # By confidence bucket
    conf_buckets = {
        'Low (30-50%)': [t for t in closed_trades if t['signal_confidence'] < 0.50],
        'Med (50-65%)': [t for t in closed_trades if 0.50 <= t['signal_confidence'] < 0.65],
        'High (65%+)':  [t for t in closed_trades if t['signal_confidence'] >= 0.65],
    }

    by_confidence = []
    for label, bucket in conf_buckets.items():
        if bucket:
            b_wins = [t for t in bucket if t['pnl'] > 0]
            by_confidence.append({
                'bucket': label,
                'trades': len(bucket),
                'win_rate': round(len(b_wins) / len(bucket) * 100, 1),
                'pnl': round(sum(t['pnl'] for t in bucket), 2)
            })

    return {
        "period_days": days,
        "total_closed": len(closed_trades),
        "total_open": len(open_trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(win_rate, 1),
        "total_pnl": round(total_pnl, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "best_trade": best,
        "worst_trade": worst,
        "risk_reward_ratio": rr_ratio,
        "profit_factor": profit_factor,
        "by_stock": by_stock,
        "by_confidence": by_confidence,
    }


if __name__ == "__main__":
    stats = get_win_rate_stats(30)
    print(f"\n📊 WIN RATE REPORT (Last {stats['period_days']} days)")
    print(f"{'='*50}")
    print(f"Total Trades  : {stats['total_closed']}")
    print(f"Win Rate      : {stats['win_rate']}%")
    print(f"Total P&L     : ₹{stats['total_pnl']:+,.0f}")
    print(f"Avg Win       : ₹{stats['avg_win']:+,.0f}")
    print(f"Avg Loss      : ₹{stats['avg_loss']:+,.0f}")
    print(f"Profit Factor : {stats['profit_factor']}")
    print(f"Risk/Reward   : {stats['risk_reward_ratio']}")