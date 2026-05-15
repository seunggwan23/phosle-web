"""모델 학습 및 추론 (model_trainer.py)"""
import numpy as np
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
import pandas as pd


def train_model(df: pd.DataFrame, feature_cols: list, target_col: str = "energy_kwh") -> dict:
    available = [c for c in feature_cols if c in df.columns]
    X = df[available].fillna(0).values
    y = df[target_col].values

    print(f"[DEBUG] 학습 Shape: X={X.shape} | 결측치={np.isnan(X).sum()}")

    scaler = StandardScaler()
    X_sc = scaler.fit_transform(X)

    tscv = TimeSeriesSplit(n_splits=5)
    mae_list, r2_list = [], []
    model = None

    for fold, (tr, val) in enumerate(tscv.split(X_sc)):
        model = xgb.XGBRegressor(
            n_estimators=300, learning_rate=0.05, max_depth=6,
            early_stopping_rounds=30, eval_metric="mae",
            random_state=42, n_jobs=-1, verbosity=0,
        )
        model.fit(X_sc[tr], y[tr], eval_set=[(X_sc[val], y[val])], verbose=False)
        yp = model.predict(X_sc[val])
        mae_list.append(mean_absolute_error(y[val], yp))
        r2_list.append(r2_score(y[val], yp))
        print(f"[DEBUG] Fold {fold+1}: MAE={mae_list[-1]:.2f} R²={r2_list[-1]:.4f}")

    fi = dict(zip(available, model.feature_importances_))
    fi = dict(sorted(fi.items(), key=lambda x: x[1], reverse=True))

    return {
        "model": model, "scaler": scaler,
        "mae": float(np.mean(mae_list)), "r2": float(np.mean(r2_list)),
        "feature_importance": fi, "feature_cols": available,
    }


def predict(model_data: dict, df: pd.DataFrame) -> np.ndarray:
    model = model_data["model"]
    scaler = model_data["scaler"]
    cols = [c for c in model_data["feature_cols"] if c in df.columns]
    X = df[cols].fillna(0).values
    X_sc = scaler.transform(X)
    return np.maximum(model.predict(X_sc), 0)
