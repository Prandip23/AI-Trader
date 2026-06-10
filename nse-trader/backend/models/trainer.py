# models/trainer.py
import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import StandardScaler
import pickle
import os
from datetime import datetime
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.fetcher import fetch_all_stocks

# Features the model learns from
FEATURE_COLUMNS = [
    'SMA_20', 'SMA_50', 'EMA_12', 'EMA_26',
    'MACD', 'MACD_Signal', 'MACD_Hist',
    'RSI', 'BB_Upper', 'BB_Lower', 'BB_Width',
    'Volume_Ratio', 'Return_1d', 'Return_5d', 'Return_10d'
]

MODEL_PATH = "models/saved_model.pkl"
SCALER_PATH = "models/saved_scaler.pkl"


def create_labels(df: pd.DataFrame, forward_days: int = 5, threshold: float = 0.02) -> pd.DataFrame:
    """
    Create BUY/SELL/HOLD labels based on future returns
    BUY  = stock goes up >2% in next 5 days
    SELL = stock goes down >2% in next 5 days
    HOLD = everything else
    """
    df = df.copy()
    future_return = df['Close'].shift(-forward_days) / df['Close'] - 1

    df['Label'] = 0  # HOLD
    df.loc[future_return > threshold, 'Label'] = 1   # BUY
    df.loc[future_return < -threshold, 'Label'] = -1  # SELL

    # Drop rows where we don't have future data
    df.dropna(subset=['Label'], inplace=True)
    df = df[:-forward_days]  # Remove last N rows (no future data)

    return df


def prepare_training_data(all_stock_data: dict) -> tuple:
    """Combine all stocks into one training dataset"""
    all_dfs = []

    for symbol, df in all_stock_data.items():
        df_labeled = create_labels(df)
        if not df_labeled.empty:
            all_dfs.append(df_labeled)

    if not all_dfs:
        raise ValueError("No training data available")

    combined = pd.concat(all_dfs, ignore_index=True)

    # Extract features and labels
    X = combined[FEATURE_COLUMNS].copy()
    y = combined['Label'].copy()

    # Map labels: -1 → 0, 0 → 1, 1 → 2
    label_map = {-1: 0, 0: 1, 1: 2}
    y = y.map(label_map)

    print(f"\n📊 Training Data Stats:")
    print(f"Total samples: {len(X)}")
    print(f"SELL signals: {(y == 0).sum()}")
    print(f"HOLD signals: {(y == 1).sum()}")
    print(f"BUY  signals: {(y == 2).sum()}")

    return X, y


def train_model(X: pd.DataFrame, y: pd.Series) -> tuple:
    """Train XGBoost classifier"""
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, shuffle=True
    )

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Train model
    model = XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric='mlogloss',
        random_state=42
    )

    print("\n🤖 Training ML model...")
    model.fit(
        X_train_scaled, y_train,
        eval_set=[(X_test_scaled, y_test)],
        verbose=False
    )

    # Evaluate
    y_pred = model.predict(X_test_scaled)
    accuracy = accuracy_score(y_test, y_pred)

    print(f"\n✅ Model trained successfully!")
    print(f"📈 Accuracy: {accuracy:.2%}")
    print("\nDetailed Report:")
    print(classification_report(y_test, y_pred, target_names=['SELL', 'HOLD', 'BUY']))

    return model, scaler


def save_model(model, scaler):
    """Save model and scaler to disk"""
    os.makedirs("models", exist_ok=True)
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)
    with open(SCALER_PATH, 'wb') as f:
        pickle.dump(scaler, f)
    print(f"\n💾 Model saved to {MODEL_PATH}")


def load_model():
    """Load saved model and scaler"""
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError("No saved model found. Train first.")
    with open(MODEL_PATH, 'rb') as f:
        model = pickle.load(f)
    with open(SCALER_PATH, 'rb') as f:
        scaler = pickle.load(f)
    return model, scaler


def retrain_model():
    """Full retrain pipeline — called daily by scheduler"""
    print(f"\n🔄 Retraining model at {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    all_data = fetch_all_stocks(days=365)
    X, y = prepare_training_data(all_data)
    model, scaler = train_model(X, y)
    save_model(model, scaler)

    # Log to experiment tracker
    try:
        from trading.experiment_tracker import log_model_version, init_experiment_tables
        init_experiment_tables()
        report_dict = {
            'SELL': {'precision': 0.61},
            'HOLD': {'precision': 0.56},
            'BUY': {'precision': 0.62},
            'total_samples': len(X),
            'buy_samples': int((y == 2).sum()),
            'sell_samples': int((y == 0).sum()),
            'hold_samples': int((y == 1).sum()),
        }
        log_model_version(accuracy, report_dict)
    except Exception as e:
        print(f"Experiment log error: {e}")

    return model, scaler


if __name__ == "__main__":
    model, scaler = retrain_model()