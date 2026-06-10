// src/App.js
import { useState, useEffect } from "react";
import axios from "axios";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine
} from "recharts";

const API = "http://localhost:8000";

const fmt = (n) => new Intl.NumberFormat("en-IN", {
  style: "currency", currency: "INR", maximumFractionDigits: 0
}).format(n);

const pct = (n) => `${n >= 0 ? "+" : ""}${Number(n).toFixed(2)}%`;

const newsSentimentColor = (s) =>
  s === "POSITIVE" ? "#22c55e" :
  s === "NEGATIVE" ? "#ef4444" :
  s === "NEUTRAL"  ? "#f59e0b" : "#64748b";

const newsSentimentEmoji = (s) =>
  s === "POSITIVE" ? "📈" :
  s === "NEGATIVE" ? "📉" :
  s === "NEUTRAL"  ? "➡️" : "📰";

const marketVerdictColor = (v) =>
  v === "STRONG_BUY"   ? "#22c55e" :
  v === "CAUTIOUS_BUY" ? "#86efac" :
  v === "NEUTRAL"      ? "#f59e0b" :
  v === "AVOID_BUY"    ? "#f97316" :
  v === "STRONG_AVOID" ? "#ef4444" : "#64748b";

export default function App() {
  const [tab, setTab] = useState("dashboard");
  const [portfolio, setPortfolio] = useState(null);
  const [signals, setSignals] = useState([]);
  const [trades, setTrades] = useState([]);
  const [history, setHistory] = useState([]);
  const [winRate, setWinRate] = useState(null);
  const [loading, setLoading] = useState(false);
  const [sessionRunning, setSessionRunning] = useState(false);
  const [retraining, setRetraining] = useState(false);

  const fetchPortfolio = () =>
    axios.get(`${API}/portfolio`).then(r => setPortfolio(r.data));

  const fetchSignals = () => {
    setLoading(true);
    axios.get(`${API}/signals`)
      .then(r => setSignals(r.data.signals))
      .finally(() => setLoading(false));
  };

  const fetchTrades = () =>
    axios.get(`${API}/trades`).then(r => setTrades(r.data.trades));

  const fetchHistory = () =>
    axios.get(`${API}/history`).then(r => setHistory(r.data.history));

  const fetchWinRate = () =>
    axios.get(`${API}/winrate?days=30`).then(r => setWinRate(r.data));

  useEffect(() => {
    fetchPortfolio();
    fetchTrades();
    fetchHistory();
    fetchWinRate();
  }, []);

  const runSession = () => {
    setSessionRunning(true);
    axios.post(`${API}/session/run`)
      .then(() => { fetchPortfolio(); fetchTrades(); fetchHistory(); fetchWinRate(); })
      .finally(() => setSessionRunning(false));
  };

  const runRetrain = () => {
    setRetraining(true);
    axios.post(`${API}/model/retrain`)
      .finally(() => setRetraining(false));
  };

  const signalColor = (s) =>
    s === "BUY" ? "#22c55e" : s === "SELL" ? "#ef4444" : "#f59e0b";

  const riskColor = (r) =>
    r === "LOW" ? "#22c55e" : r === "HIGH" ? "#ef4444" : "#f59e0b";

  const chartData = [...history].reverse().map(h => ({
    date: h.date,
    value: Math.round(h.portfolio_value),
    pnl: Math.round(h.daily_pnl)
  }));

  const marketCtx = signals.find(s => s.market_verdict) || null;

  return (
    <div style={{
      minHeight: "100vh", background: "#0f172a",
      color: "#e2e8f0", fontFamily: "'Inter', sans-serif"
    }}>
      {/* Header */}
      <div style={{
        background: "#1e293b", borderBottom: "1px solid #334155",
        padding: "16px 32px", display: "flex",
        justifyContent: "space-between", alignItems: "center"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 24 }}>📈</span>
          <div>
            <div style={{ fontWeight: 700, fontSize: 18, color: "#f1f5f9" }}>NSE AI Trader</div>
            <div style={{ fontSize: 12, color: "#64748b" }}>Powered by XGBoost + Claude AI</div>
          </div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button onClick={runSession} disabled={sessionRunning} style={{
            background: sessionRunning ? "#334155" : "#22c55e",
            color: "#fff", border: "none", borderRadius: 8,
            padding: "8px 16px", cursor: "pointer", fontWeight: 600, fontSize: 13
          }}>
            {sessionRunning ? "⏳ Running..." : "▶ Run Session"}
          </button>
          <button onClick={runRetrain} disabled={retraining} style={{
            background: retraining ? "#334155" : "#3b82f6",
            color: "#fff", border: "none", borderRadius: 8,
            padding: "8px 16px", cursor: "pointer", fontWeight: 600, fontSize: 13
          }}>
            {retraining ? "⏳ Training..." : "🔄 Retrain Model"}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div style={{
        display: "flex", gap: 4, padding: "16px 32px 0",
        borderBottom: "1px solid #1e293b"
      }}>
        {["dashboard", "signals", "trades", "performance"].map(t => (
          <button key={t} onClick={() => {
            setTab(t);
            if (t === "signals") fetchSignals();
            if (t === "performance") fetchWinRate();
          }} style={{
            background: tab === t ? "#3b82f6" : "transparent",
            color: tab === t ? "#fff" : "#64748b",
            border: "none", borderRadius: "8px 8px 0 0",
            padding: "8px 20px", cursor: "pointer",
            fontWeight: 600, fontSize: 14, textTransform: "capitalize"
          }}>{t}</button>
        ))}
      </div>

      <div style={{ padding: "24px 32px" }}>

        {/* DASHBOARD TAB */}
        {tab === "dashboard" && portfolio && (
          <div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 24 }}>
              {[
                { label: "Portfolio Value", value: fmt(portfolio.total_value), color: "#f1f5f9" },
                { label: "Total P&L", value: fmt(portfolio.pnl), color: portfolio.pnl >= 0 ? "#22c55e" : "#ef4444" },
                { label: "Return", value: pct(portfolio.pnl_pct), color: portfolio.pnl_pct >= 0 ? "#22c55e" : "#ef4444" },
                { label: "Cash Available", value: fmt(portfolio.cash), color: "#60a5fa" },
              ].map(stat => (
                <div key={stat.label} style={{
                  background: "#1e293b", borderRadius: 12,
                  padding: "20px 24px", border: "1px solid #334155"
                }}>
                  <div style={{ fontSize: 12, color: "#64748b", marginBottom: 8 }}>{stat.label}</div>
                  <div style={{ fontSize: 22, fontWeight: 700, color: stat.color }}>{stat.value}</div>
                </div>
              ))}
            </div>

            <div style={{
              background: "#1e293b", borderRadius: 12,
              padding: 24, border: "1px solid #334155", marginBottom: 24
            }}>
              <div style={{ fontWeight: 600, marginBottom: 16, color: "#f1f5f9" }}>Portfolio Performance</div>
              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="date" stroke="#64748b" fontSize={12} />
                    <YAxis stroke="#64748b" fontSize={12}
                      tickFormatter={v => `₹${(v / 100000).toFixed(1)}L`} />
                    <Tooltip
                      contentStyle={{ background: "#0f172a", border: "1px solid #334155" }}
                      formatter={v => [fmt(v), "Portfolio"]} />
                    <ReferenceLine y={1000000} stroke="#64748b" strokeDasharray="4 4" />
                    <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ color: "#64748b", textAlign: "center", padding: 40 }}>
                  Run your first session to see performance chart
                </div>
              )}
            </div>

            <div style={{ background: "#1e293b", borderRadius: 12, padding: 24, border: "1px solid #334155" }}>
              <div style={{ fontWeight: 600, marginBottom: 16, color: "#f1f5f9" }}>
                Open Positions ({portfolio.open_positions?.length || 0})
              </div>
              {portfolio.open_positions?.length > 0 ? (
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
                  <thead>
                    <tr style={{ color: "#64748b", borderBottom: "1px solid #334155" }}>
                      {["Symbol", "Qty", "Buy Price", "Stop Loss", "Target", "Value", "Risk"].map(h => (
                        <th key={h} style={{ padding: "8px 12px", textAlign: "left" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {portfolio.open_positions.map(p => (
                      <tr key={p.id} style={{ borderBottom: "1px solid #1e293b" }}>
                        <td style={{ padding: "10px 12px", fontWeight: 600, color: "#60a5fa" }}>{p.symbol}</td>
                        <td style={{ padding: "10px 12px" }}>{p.quantity}</td>
                        <td style={{ padding: "10px 12px" }}>₹{p.price}</td>
                        <td style={{ padding: "10px 12px", color: "#ef4444" }}>₹{p.stop_loss}</td>
                        <td style={{ padding: "10px 12px", color: "#22c55e" }}>₹{p.target}</td>
                        <td style={{ padding: "10px 12px" }}>{fmt(p.value)}</td>
                        <td style={{ padding: "10px 12px" }}>
                          <span style={{
                            background: riskColor(p.risk_level) + "22",
                            color: riskColor(p.risk_level),
                            padding: "2px 8px", borderRadius: 4, fontSize: 12
                          }}>{p.risk_level}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div style={{ color: "#64748b", textAlign: "center", padding: 20 }}>
                  No open positions. Run a session to start trading.
                </div>
              )}
            </div>
          </div>
        )}

        {/* SIGNALS TAB */}
        {tab === "signals" && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 20, alignItems: "flex-start" }}>
              <div style={{ fontWeight: 600, fontSize: 16, color: "#f1f5f9" }}>Today's AI Signals</div>
              <button onClick={fetchSignals} style={{
                background: "#3b82f6", color: "#fff", border: "none",
                borderRadius: 8, padding: "8px 16px", cursor: "pointer", fontSize: 13
              }}>
                {loading ? "⏳ Fetching..." : "🔄 Refresh Signals"}
              </button>
            </div>

            {/* Market Context Banner */}
            {marketCtx && !loading && (
              <div style={{
                background: "#1e293b", borderRadius: 12, padding: "16px 20px",
                marginBottom: 20, border: `1px solid ${marketVerdictColor(marketCtx.market_verdict)}44`,
                display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 16
              }}>
                {[
                  { label: "Market Verdict", value: marketCtx.market_verdict?.replace(/_/g, " "), color: marketVerdictColor(marketCtx.market_verdict) },
                  { label: "India VIX", value: marketCtx.vix, color: marketCtx.vix > 20 ? "#ef4444" : marketCtx.vix > 15 ? "#f59e0b" : "#22c55e" },
                  { label: "VIX Signal", value: marketCtx.vix_signal?.replace(/_/g, " "), color: "#94a3b8" },
                  { label: "Nifty Trend", value: marketCtx.nifty_trend, color: marketCtx.nifty_trend === "BULLISH" ? "#22c55e" : marketCtx.nifty_trend === "BEARISH" ? "#ef4444" : "#f59e0b" },
                  { label: "Breadth", value: `${marketCtx.breadth_pct}% bullish`, color: marketCtx.breadth_pct >= 60 ? "#22c55e" : marketCtx.breadth_pct >= 40 ? "#f59e0b" : "#ef4444" },
                ].map(item => (
                  <div key={item.label}>
                    <div style={{ fontSize: 11, color: "#64748b", marginBottom: 4 }}>{item.label}</div>
                    <div style={{ fontSize: 13, fontWeight: 700, color: item.color }}>{item.value}</div>
                  </div>
                ))}
              </div>
            )}

            {loading && (
              <div style={{ textAlign: "center", padding: 60, color: "#64748b" }}>
                ⏳ Fetching signals, news and running AI analysis...
              </div>
            )}

            {!loading && signals.length === 0 && (
              <div style={{ textAlign: "center", padding: 60, color: "#64748b" }}>
                Click "Refresh Signals" to generate today's calls
              </div>
            )}

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(360px, 1fr))", gap: 16 }}>
              {signals.filter(s => s.final_signal !== "HOLD").map(s => (
                <div key={s.symbol + s.price} style={{
                  background: "#1e293b", borderRadius: 12,
                  border: `1px solid ${signalColor(s.final_signal)}44`,
                  padding: 20
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: 16, color: "#f1f5f9" }}>
                        {s.symbol.replace(".NS", "").replace(".BO", "")}
                      </div>
                      {s.news_sentiment && s.news_sentiment !== "NO_NEWS" && (
                        <div style={{ fontSize: 11, color: newsSentimentColor(s.news_sentiment), marginTop: 2 }}>
                          {newsSentimentEmoji(s.news_sentiment)} News: {s.news_sentiment}
                        </div>
                      )}
                    </div>
                    <span style={{
                      background: signalColor(s.final_signal) + "22",
                      color: signalColor(s.final_signal),
                      padding: "4px 12px", borderRadius: 6, fontWeight: 700,
                      height: "fit-content"
                    }}>{s.final_signal}</span>
                  </div>

                  <div style={{ fontSize: 24, fontWeight: 700, marginBottom: 12 }}>
                    ₹{s.price.toLocaleString("en-IN")}
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8, marginBottom: 12, fontSize: 12 }}>
                    <div style={{ background: "#0f172a", borderRadius: 6, padding: 8 }}>
                      <div style={{ color: "#64748b" }}>Confidence</div>
                      <div style={{ fontWeight: 600 }}>{(s.ml_confidence * 100).toFixed(1)}%</div>
                    </div>
                    <div style={{ background: "#0f172a", borderRadius: 6, padding: 8 }}>
                      <div style={{ color: "#64748b" }}>RSI</div>
                      <div style={{ fontWeight: 600, color: s.rsi < 40 ? "#22c55e" : s.rsi > 60 ? "#ef4444" : "#f1f5f9" }}>
                        {s.rsi}
                      </div>
                    </div>
                    <div style={{ background: "#0f172a", borderRadius: 6, padding: 8 }}>
                      <div style={{ color: "#64748b" }}>Volume</div>
                      <div style={{ fontWeight: 600 }}>{s.volume_ratio}x</div>
                    </div>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 12, fontSize: 12 }}>
                    <div style={{ background: "#ef444422", borderRadius: 6, padding: 8 }}>
                      <div style={{ color: "#64748b" }}>Stop Loss</div>
                      <div style={{ color: "#ef4444", fontWeight: 600 }}>-{s.stop_loss_pct}%</div>
                    </div>
                    <div style={{ background: "#22c55e22", borderRadius: 6, padding: 8 }}>
                      <div style={{ color: "#64748b" }}>Target</div>
                      <div style={{ color: "#22c55e", fontWeight: 600 }}>+{s.target_pct}%</div>
                    </div>
                  </div>

                  {s.ai_reasoning && s.ai_reasoning !== "AI validation skipped" && (
                    <div style={{
                      background: "#0f172a", borderRadius: 8, padding: 12,
                      fontSize: 12, color: "#94a3b8", borderLeft: "3px solid #3b82f6", marginBottom: 8
                    }}>
                      🤖 {s.ai_reasoning}
                    </div>
                  )}

                  {s.news_headlines && s.news_headlines.length > 0 && (
                    <div style={{
                      background: "#0f172a", borderRadius: 8, padding: 12, fontSize: 11,
                      borderLeft: `3px solid ${newsSentimentColor(s.news_sentiment)}`
                    }}>
                      <div style={{ color: "#64748b", marginBottom: 6, fontWeight: 600 }}>📰 Latest News</div>
                      {s.news_headlines.slice(0, 3).map((headline, i) => (
                        <div key={i} style={{
                          color: "#94a3b8", marginBottom: 4, paddingBottom: 4,
                          borderBottom: i < 2 ? "1px solid #1e293b" : "none"
                        }}>
                          • {headline.length > 80 ? headline.slice(0, 80) + "..." : headline}
                        </div>
                      ))}
                    </div>
                  )}

                  {s.key_concern && (
                    <div style={{ fontSize: 11, color: "#f59e0b", marginTop: 8 }}>
                      ⚠️ {s.key_concern}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TRADES TAB */}
        {tab === "trades" && (
          <div>
            <div style={{ fontWeight: 600, fontSize: 16, color: "#f1f5f9", marginBottom: 20 }}>Trade History</div>
            <div style={{ background: "#1e293b", borderRadius: 12, border: "1px solid #334155", overflow: "hidden" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ background: "#0f172a", color: "#64748b" }}>
                    {["Symbol", "Action", "Price", "Qty", "Value", "Status", "P&L", "Date"].map(h => (
                      <th key={h} style={{ padding: "12px 16px", textAlign: "left" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {trades.length === 0 ? (
                    <tr>
                      <td colSpan={8} style={{ padding: 40, textAlign: "center", color: "#64748b" }}>
                        No trades yet. Run a session to start.
                      </td>
                    </tr>
                  ) : trades.map(t => (
                    <tr key={t.id} style={{ borderBottom: "1px solid #1e293b" }}>
                      <td style={{ padding: "12px 16px", fontWeight: 600, color: "#60a5fa" }}>
                        {t.symbol.replace(".NS", "").replace(".BO", "")}
                      </td>
                      <td style={{ padding: "12px 16px" }}>
                        <span style={{ color: signalColor(t.action), fontWeight: 600 }}>{t.action}</span>
                      </td>
                      <td style={{ padding: "12px 16px" }}>₹{t.price}</td>
                      <td style={{ padding: "12px 16px" }}>{t.quantity}</td>
                      <td style={{ padding: "12px 16px" }}>{fmt(t.value)}</td>
                      <td style={{ padding: "12px 16px" }}>
                        <span style={{
                          background: t.status === "OPEN" ? "#3b82f622" :
                            t.status === "TARGET_HIT" ? "#22c55e22" : "#ef444422",
                          color: t.status === "OPEN" ? "#3b82f6" :
                            t.status === "TARGET_HIT" ? "#22c55e" : "#ef4444",
                          padding: "2px 8px", borderRadius: 4, fontSize: 11
                        }}>{t.status}</span>
                      </td>
                      <td style={{ padding: "12px 16px", color: t.pnl >= 0 ? "#22c55e" : "#ef4444" }}>
                        {t.pnl ? fmt(t.pnl) : "—"}
                      </td>
                      <td style={{ padding: "12px 16px", color: "#64748b", fontSize: 11 }}>
                        {t.created_at?.slice(0, 10)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* PERFORMANCE TAB */}
        {tab === "performance" && winRate && (
          <div>
            <div style={{ fontWeight: 600, fontSize: 16, color: "#f1f5f9", marginBottom: 20 }}>
              Performance — Last {winRate.period_days} Days
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 24 }}>
              {[
                { label: "Win Rate", value: `${winRate.win_rate}%`, color: winRate.win_rate >= 50 ? "#22c55e" : "#ef4444" },
                { label: "Total P&L", value: fmt(winRate.total_pnl), color: winRate.total_pnl >= 0 ? "#22c55e" : "#ef4444" },
                { label: "Profit Factor", value: winRate.profit_factor, color: winRate.profit_factor >= 1.5 ? "#22c55e" : "#f59e0b" },
                { label: "Risk/Reward", value: `1 : ${winRate.risk_reward_ratio}`, color: "#60a5fa" },
              ].map(stat => (
                <div key={stat.label} style={{
                  background: "#1e293b", borderRadius: 12,
                  padding: "20px 24px", border: "1px solid #334155"
                }}>
                  <div style={{ fontSize: 12, color: "#64748b", marginBottom: 8 }}>{stat.label}</div>
                  <div style={{ fontSize: 22, fontWeight: 700, color: stat.color }}>{stat.value}</div>
                </div>
              ))}
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 24 }}>
              <div style={{ background: "#1e293b", borderRadius: 12, padding: 24, border: "1px solid #334155" }}>
                <div style={{ fontWeight: 600, marginBottom: 16, color: "#f1f5f9" }}>Trade Summary</div>
                {[
                  { label: "Total Closed Trades", value: winRate.total_closed },
                  { label: "Winning Trades", value: winRate.wins, color: "#22c55e" },
                  { label: "Losing Trades", value: winRate.losses, color: "#ef4444" },
                  { label: "Open Positions", value: winRate.total_open, color: "#60a5fa" },
                  { label: "Avg Win", value: fmt(winRate.avg_win), color: "#22c55e" },
                  { label: "Avg Loss", value: fmt(winRate.avg_loss), color: "#ef4444" },
                ].map(row => (
                  <div key={row.label} style={{
                    display: "flex", justifyContent: "space-between",
                    padding: "8px 0", borderBottom: "1px solid #1e293b"
                  }}>
                    <span style={{ color: "#64748b", fontSize: 13 }}>{row.label}</span>
                    <span style={{ fontWeight: 600, color: row.color || "#f1f5f9" }}>{row.value}</span>
                  </div>
                ))}
              </div>

              <div style={{ background: "#1e293b", borderRadius: 12, padding: 24, border: "1px solid #334155" }}>
                <div style={{ fontWeight: 600, marginBottom: 16, color: "#f1f5f9" }}>Win Rate by Confidence</div>
                {winRate.by_confidence.length === 0 ? (
                  <div style={{ color: "#64748b", textAlign: "center", padding: 20 }}>Not enough data yet</div>
                ) : winRate.by_confidence.map(b => (
                  <div key={b.bucket} style={{ marginBottom: 16 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                      <span style={{ fontSize: 13, color: "#94a3b8" }}>{b.bucket}</span>
                      <span style={{ fontSize: 13, fontWeight: 600 }}>{b.win_rate}% ({b.trades} trades)</span>
                    </div>
                    <div style={{ background: "#0f172a", borderRadius: 4, height: 8 }}>
                      <div style={{
                        width: `${b.win_rate}%`, height: 8, borderRadius: 4,
                        background: b.win_rate >= 50 ? "#22c55e" : "#ef4444"
                      }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {(winRate.best_trade || winRate.worst_trade) && (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 24 }}>
                {winRate.best_trade && (
                  <div style={{ background: "#1e293b", borderRadius: 12, padding: 20, border: "1px solid #22c55e44" }}>
                    <div style={{ color: "#22c55e", fontWeight: 600, marginBottom: 8 }}>🏆 Best Trade</div>
                    <div style={{ fontSize: 18, fontWeight: 700 }}>{winRate.best_trade.symbol?.replace(".NS", "")}</div>
                    <div style={{ color: "#22c55e", fontSize: 20, fontWeight: 700 }}>{fmt(winRate.best_trade.pnl)}</div>
                    <div style={{ color: "#64748b", fontSize: 12, marginTop: 4 }}>{winRate.best_trade.created_at?.slice(0, 10)}</div>
                  </div>
                )}
                {winRate.worst_trade && (
                  <div style={{ background: "#1e293b", borderRadius: 12, padding: 20, border: "1px solid #ef444444" }}>
                    <div style={{ color: "#ef4444", fontWeight: 600, marginBottom: 8 }}>📉 Worst Trade</div>
                    <div style={{ fontSize: 18, fontWeight: 700 }}>{winRate.worst_trade.symbol?.replace(".NS", "")}</div>
                    <div style={{ color: "#ef4444", fontSize: 20, fontWeight: 700 }}>{fmt(winRate.worst_trade.pnl)}</div>
                    <div style={{ color: "#64748b", fontSize: 12, marginTop: 4 }}>{winRate.worst_trade.created_at?.slice(0, 10)}</div>
                  </div>
                )}
              </div>
            )}

            <div style={{ background: "#1e293b", borderRadius: 12, padding: 24, border: "1px solid #334155" }}>
              <div style={{ fontWeight: 600, marginBottom: 16, color: "#f1f5f9" }}>Performance by Stock</div>
              {winRate.by_stock.length === 0 ? (
                <div style={{ color: "#64748b", textAlign: "center", padding: 20 }}>
                  No closed trades yet — run sessions for 30 days to see stock performance
                </div>
              ) : (
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ color: "#64748b", borderBottom: "1px solid #334155" }}>
                      {["Stock", "Trades", "Win Rate", "Total P&L"].map(h => (
                        <th key={h} style={{ padding: "8px 12px", textAlign: "left" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {winRate.by_stock.map(s => (
                      <tr key={s.symbol} style={{ borderBottom: "1px solid #0f172a" }}>
                        <td style={{ padding: "10px 12px", fontWeight: 600, color: "#60a5fa" }}>{s.symbol}</td>
                        <td style={{ padding: "10px 12px" }}>{s.trades}</td>
                        <td style={{ padding: "10px 12px", color: s.win_rate >= 50 ? "#22c55e" : "#ef4444" }}>{s.win_rate}%</td>
                        <td style={{ padding: "10px 12px", color: s.pnl >= 0 ? "#22c55e" : "#ef4444", fontWeight: 600 }}>
                          {fmt(s.pnl)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}

        {tab === "performance" && !winRate && (
          <div style={{ textAlign: "center", padding: 60, color: "#64748b" }}>
            ⏳ Loading performance data...
          </div>
        )}

      </div>
    </div>
  );
}