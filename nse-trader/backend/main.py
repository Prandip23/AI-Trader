# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import sys
import os
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from engine.signals import generate_signals
from trading.paper_trader import init_db, run_daily_session, get_portfolio, get_open_positions, DB_PATH
from models.trainer import retrain_model
from trading.win_tracker import get_win_rate_stats
from trading.experiment_tracker import get_experiment_summary, init_experiment_tables

app = FastAPI(title="NSE AI Trader")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Daily scheduler — retrain + trade at 9:30 AM IST
scheduler = BackgroundScheduler()
scheduler.add_job(retrain_model, 'cron', hour=9, minute=30)
scheduler.add_job(run_daily_session, 'cron', hour=9, minute=45)
scheduler.start()


@app.get("/")
def root():
    return {"status": "NSE AI Trader Running", "time": datetime.now().isoformat()}


@app.get("/portfolio")
def portfolio():
    conn = sqlite3.connect(DB_PATH)
    p = get_portfolio(conn)
    positions = get_open_positions(conn)
    for pos in positions:
        pos['current_pnl'] = 0
        pos['pnl_pct'] = 0
    conn.close()
    return {
        "cash": p['cash'],
        "total_value": p['total_value'],
        "pnl": p['total_value'] - 1_000_000,
        "pnl_pct": round((p['total_value'] / 1_000_000 - 1) * 100, 2),
        "open_positions": positions
    }


@app.get("/signals")
def signals():
    data = generate_signals(use_ai=True)
    return {"signals": data, "generated_at": datetime.now().isoformat()}


@app.get("/trades")
def trades():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM trades ORDER BY created_at DESC LIMIT 50")
    cols = [d[0] for d in c.description]
    rows = [dict(zip(cols, row)) for row in c.fetchall()]
    conn.close()
    return {"trades": rows}


@app.get("/history")
def history():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM daily_summary ORDER BY date DESC LIMIT 30")
    cols = [d[0] for d in c.description]
    rows = [dict(zip(cols, row)) for row in c.fetchall()]
    conn.close()
    return {"history": rows}


@app.get("/winrate")
def winrate(days: int = 30):
    return get_win_rate_stats(days)


@app.get("/experiments")
def experiments():
    return get_experiment_summary()


@app.post("/session/run")
def run_session():
    init_db()
    total = run_daily_session()
    return {"status": "Session complete", "portfolio_value": total}


@app.post("/model/retrain")
def retrain():
    retrain_model()
    return {"status": "Model retrained", "time": datetime.now().isoformat()}