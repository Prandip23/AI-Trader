from engine.signals import generate_signals

signals = generate_signals(use_ai=True)
print("\n===== FULL SIGNAL DETAILS =====")
for s in signals:
    print(f"\n{s['symbol']}")
    print(f"  ML Signal  : {s['ml_signal']} ({s['ml_confidence']:.1%})")
    print(f"  AI Signal  : {s['ai_signal']}")
    print(f"  Final      : {s['final_signal']}")
    print(f"  RSI        : {s['rsi']}")
    print(f"  Reasoning  : {s['ai_reasoning']}")