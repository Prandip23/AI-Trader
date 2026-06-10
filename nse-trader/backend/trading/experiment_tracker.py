# trading/experiment_tracker.py
import sqlite3
import json
import os
from datetime import datetime

DB_PATH = "trading/paper_trades.db"


def init_experiment_tables():
    """Add experiment tracking tables to existing DB"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Every model retrain
    c.execute('''CREATE TABLE IF NOT EXISTS model_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        version TEXT,
        trained_at TEXT,
        accuracy REAL,
        sell_precision REAL,
        hold_precision REAL,
        buy_precision REAL,
        total_samples INTEGER,
        buy_samples INTEGER,
        sell_samples INTEGER,
        hold_samples INTEGER,
        parameters TEXT,
        notes TEXT
    )''')

    # Every signal generated — full context
    c.execute('''CREATE TABLE IF NOT EXISTS signal_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        symbol TEXT,
        ml_signal TEXT,
        ml_confidence REAL,
        ai_signal TEXT,
        final_signal TEXT,
        price REAL,
        rsi REAL,
        macd REAL,
        macd_signal REAL,
        volume_ratio REAL,
        sma20_dist REAL,
        sma50_dist REAL,
        bb_position REAL,
        return_1d REAL,
        return_5d REAL,
        ai_reasoning TEXT,
        risk_level TEXT,
        stop_loss_pct REAL,
        target_pct REAL,
        key_concern TEXT,
        confidence_threshold REAL,
        prompt_version TEXT,
        model_version TEXT,
        was_executed INTEGER DEFAULT 0,
        created_at TEXT
    )''')

    # Closed trade outcomes with full entry context
    c.execute('''CREATE TABLE IF NOT EXISTS trade_outcomes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trade_id INTEGER,
        symbol TEXT,
        entry_price REAL,
        exit_price REAL,
        quantity INTEGER,
        entry_date TEXT,
        exit_date TEXT,
        exit_reason TEXT,
        pnl REAL,
        pnl_pct REAL,
        hold_days INTEGER,
        entry_rsi REAL,
        entry_volume_ratio REAL,
        entry_macd REAL,
        entry_confidence REAL,
        entry_signal TEXT,
        ai_reasoning TEXT,
        market_phase TEXT,
        confidence_threshold REAL,
        prompt_version TEXT,
        model_version TEXT
    )''')

    # Every parameter change you make
    c.execute('''CREATE TABLE IF NOT EXISTS experiment_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        parameter_changed TEXT,
        old_value TEXT,
        new_value TEXT,
        reason TEXT,
        win_rate_before REAL,
        trades_before INTEGER,
        notes TEXT,
        created_at TEXT
    )''')

    # Daily market context
    c.execute('''CREATE TABLE IF NOT EXISTS market_context (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT UNIQUE,
        nifty_close REAL,
        nifty_change_pct REAL,
        market_phase TEXT,
        total_signals INTEGER,
        buy_signals INTEGER,
        sell_signals INTEGER,
        hold_signals INTEGER,
        trades_executed INTEGER,
        created_at TEXT
    )''')

    conn.commit()
    conn.close()
    print("✅ Experiment tracking tables initialized")


def log_model_version(accuracy: float, report: dict, parameters: dict = None):
    """Log every model retrain"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    version = datetime.now().strftime("%Y%m%d_%H%M")

    c.execute('''INSERT INTO model_versions
        (version, trained_at, accuracy, sell_precision, hold_precision,
         buy_precision, total_samples, buy_samples, sell_samples, hold_samples,
         parameters, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (version,
         datetime.now().isoformat(),
         accuracy,
         report.get('SELL', {}).get('precision', 0),
         report.get('HOLD', {}).get('precision', 0),
         report.get('BUY', {}).get('precision', 0),
         report.get('total_samples', 0),
         report.get('buy_samples', 0),
         report.get('sell_samples', 0),
         report.get('hold_samples', 0),
         json.dumps(parameters or {}),
         f"Auto retrain - {datetime.now().strftime('%Y-%m-%d')}"
    ))

    conn.commit()
    conn.close()
    print(f"✅ Model version {version} logged")
    return version


def log_signals(signals: list, confidence_threshold: float,
                prompt_version: str = "v1", model_version: str = "latest"):
    """Log all signals generated in a session"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    date = datetime.now().strftime('%Y-%m-%d')

    for s in signals:
        c.execute('''INSERT INTO signal_log
            (date, symbol, ml_signal, ml_confidence, ai_signal, final_signal,
             price, rsi, macd, macd_signal, volume_ratio,
             sma20_dist, sma50_dist, bb_position,
             return_1d, return_5d, ai_reasoning, risk_level,
             stop_loss_pct, target_pct, key_concern,
             confidence_threshold, prompt_version, model_version,
             was_executed, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (date,
             s.get('symbol'),
             s.get('ml_signal'),
             s.get('ml_confidence'),
             s.get('ai_signal'),
             s.get('final_signal'),
             s.get('price'),
             s.get('rsi'),
             s.get('macd'),
             s.get('macd_signal', 0),
             s.get('volume_ratio'),
             s.get('sma20_dist', 0),
             s.get('sma50_dist', 0),
             s.get('bb_position', 0),
             s.get('return_1d', 0),
             s.get('return_5d', 0),
             s.get('ai_reasoning', ''),
             s.get('risk_level', 'MEDIUM'),
             s.get('stop_loss_pct', 2.5),
             s.get('target_pct', 5.0),
             s.get('key_concern', ''),
             confidence_threshold,
             prompt_version,
             model_version,
             1 if s.get('final_signal') in ['BUY', 'SELL'] else 0,
             datetime.now().isoformat()
        ))

    conn.commit()
    conn.close()
    print(f"✅ {len(signals)} signals logged to experiment tracker")


def log_trade_outcome(trade: dict, exit_price: float,
                      exit_reason: str, model_version: str = "latest",
                      prompt_version: str = "v1",
                      confidence_threshold: float = 0.40):
    """Log a closed trade with full context"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    entry_date = trade.get('created_at', '')[:10]
    exit_date = datetime.now().strftime('%Y-%m-%d')

    try:
        hold_days = (datetime.strptime(exit_date, '%Y-%m-%d') -
                     datetime.strptime(entry_date, '%Y-%m-%d')).days
    except:
        hold_days = 0

    pnl = (exit_price - trade['price']) * trade['quantity']
    pnl_pct = (exit_price - trade['price']) / trade['price'] * 100

    c.execute('''INSERT INTO trade_outcomes
        (trade_id, symbol, entry_price, exit_price, quantity,
         entry_date, exit_date, exit_reason, pnl, pnl_pct, hold_days,
         entry_rsi, entry_volume_ratio, entry_macd, entry_confidence,
         entry_signal, ai_reasoning, market_phase,
         confidence_threshold, prompt_version, model_version)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        (trade.get('id'),
         trade.get('symbol'),
         trade.get('price'),
         exit_price,
         trade.get('quantity'),
         entry_date,
         exit_date,
         exit_reason,
         round(pnl, 2),
         round(pnl_pct, 2),
         hold_days,
         trade.get('entry_rsi', 0),
         trade.get('entry_volume_ratio', 0),
         trade.get('entry_macd', 0),
         trade.get('signal_confidence', 0),
         trade.get('action', 'BUY'),
         trade.get('reasoning', ''),
         'UNKNOWN',
         confidence_threshold,
         prompt_version,
         model_version
    ))

    conn.commit()
    conn.close()


def log_experiment(parameter: str, old_value: str, new_value: str,
                   reason: str, win_rate_before: float = 0, trades_before: int = 0):
    """Log every parameter change you make"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''INSERT INTO experiment_log
        (date, parameter_changed, old_value, new_value, reason,
         win_rate_before, trades_before, created_at)
        VALUES (?,?,?,?,?,?,?,?)''',
        (datetime.now().strftime('%Y-%m-%d'),
         parameter, old_value, new_value, reason,
         win_rate_before, trades_before,
         datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()
    print(f"✅ Experiment logged: {parameter} changed {old_value} → {new_value}")


def log_market_context(signals: list, trades_executed: int):
    """Log daily market summary"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    date = datetime.now().strftime('%Y-%m-%d')

    buy_signals = len([s for s in signals if s['final_signal'] == 'BUY'])
    sell_signals = len([s for s in signals if s['final_signal'] == 'SELL'])
    hold_signals = len([s for s in signals if s['final_signal'] == 'HOLD'])

    market_phase = 'BEARISH' if sell_signals > buy_signals else \
                   'BULLISH' if buy_signals > sell_signals else 'NEUTRAL'

    try:
        c.execute('''INSERT OR REPLACE INTO market_context
            (date, market_phase, total_signals, buy_signals,
             sell_signals, hold_signals, trades_executed, created_at)
            VALUES (?,?,?,?,?,?,?,?)''',
            (date, market_phase, len(signals),
             buy_signals, sell_signals, hold_signals,
             trades_executed, datetime.now().isoformat()
        ))
        conn.commit()
    except Exception as e:
        print(f"Market context log error: {e}")
    finally:
        conn.close()


def get_experiment_summary() -> dict:
    """Get full experiment summary for analysis"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Model version history
    c.execute("SELECT version, trained_at, accuracy FROM model_versions ORDER BY trained_at DESC LIMIT 10")
    model_history = [{'version': r[0], 'date': r[1][:10], 'accuracy': round(r[2]*100, 1)}
                     for r in c.fetchall()]

    # Signal accuracy by confidence bucket
    c.execute('''SELECT
        CASE
            WHEN ml_confidence < 0.45 THEN 'Low (40-45%)'
            WHEN ml_confidence < 0.55 THEN 'Med (45-55%)'
            WHEN ml_confidence < 0.65 THEN 'High (55-65%)'
            ELSE 'Very High (65%+)'
        END as bucket,
        COUNT(*) as total,
        SUM(was_executed) as executed
        FROM signal_log
        WHERE final_signal IN ('BUY', 'SELL')
        GROUP BY bucket''')
    signal_buckets = [{'bucket': r[0], 'total': r[1], 'executed': r[2]}
                      for r in c.fetchall()]

    # Trade outcomes summary
    c.execute('''SELECT
        COUNT(*) as total,
        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
        AVG(pnl) as avg_pnl,
        AVG(hold_days) as avg_hold_days,
        exit_reason,
        COUNT(*) as count
        FROM trade_outcomes
        GROUP BY exit_reason''')
    outcomes = [{'exit_reason': r[4], 'count': r[5],
                 'avg_pnl': round(r[2] or 0, 2)}
                for r in c.fetchall()]

    # Parameter change history
    c.execute("SELECT * FROM experiment_log ORDER BY created_at DESC LIMIT 20")
    cols = [d[0] for d in c.description]
    experiments = [dict(zip(cols, row)) for row in c.fetchall()]

    # RSI performance analysis
    c.execute('''SELECT
        CASE
            WHEN o.entry_rsi < 30 THEN 'Extremely Oversold (<30)'
            WHEN o.entry_rsi < 40 THEN 'Oversold (30-40)'
            WHEN o.entry_rsi < 50 THEN 'Neutral Low (40-50)'
            WHEN o.entry_rsi < 60 THEN 'Neutral High (50-60)'
            ELSE 'Overbought (>60)'
        END as rsi_bucket,
        COUNT(*) as trades,
        SUM(CASE WHEN o.pnl > 0 THEN 1 ELSE 0 END) as wins,
        ROUND(AVG(o.pnl), 2) as avg_pnl
        FROM trade_outcomes o
        GROUP BY rsi_bucket
        ORDER BY avg_pnl DESC''')
    rsi_analysis = [{'rsi_bucket': r[0], 'trades': r[1],
                     'wins': r[2], 'avg_pnl': r[3]}
                    for r in c.fetchall()]

    conn.close()

    return {
        'model_history': model_history,
        'signal_buckets': signal_buckets,
        'outcomes_by_reason': outcomes,
        'experiments': experiments,
        'rsi_analysis': rsi_analysis
    }


if __name__ == "__main__":
    init_experiment_tables()

    # Log today's parameter change
    log_experiment(
        parameter="confidence_threshold",
        old_value="0.50",
        new_value="0.40",
        reason="Too few trades executing — Claude overriding most signals to HOLD",
        win_rate_before=0,
        trades_before=0
    )
    log_experiment(
        parameter="claude_prompt",
        old_value="strict",
        new_value="moderate — low volume not sufficient reason to override BUY",
        reason="App was generating 0 trades due to Claude being too conservative",
        win_rate_before=0,
        trades_before=0
    )

    print("\n📊 Experiment Summary:")
    summary = get_experiment_summary()
    print(f"Model versions tracked: {len(summary['model_history'])}")
    print(f"Parameter changes logged: {len(summary['experiments'])}")
    for exp in summary['experiments']:
        print(f"  → {exp['parameter_changed']}: {exp['old_value']} → {exp['new_value']}")