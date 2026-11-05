from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

FEATURES = [
    "lag_1", "lag_7", "lag_14", "rolling_7", "rolling_28",
    "day_of_week", "day_of_month", "week_of_year", "month",
]


@dataclass
class ForecastResult:
    product_id: str
    model_name: str | None
    metrics: dict[str, float] | None
    forecasts: list[dict]
    warning: str | None
    uncertainty: dict[str, float] | None


def _features(series: pd.Series) -> pd.DataFrame:
    frame = pd.DataFrame({"demand": series.astype(float)})
    frame["lag_1"] = frame["demand"].shift(1)
    frame["lag_7"] = frame["demand"].shift(7)
    frame["lag_14"] = frame["demand"].shift(14)
    frame["rolling_7"] = frame["demand"].shift(1).rolling(7, min_periods=7).mean()
    frame["rolling_28"] = frame["demand"].shift(1).rolling(28, min_periods=14).mean()
    frame["day_of_week"] = frame.index.dayofweek
    frame["day_of_month"] = frame.index.day
    frame["week_of_year"] = frame.index.isocalendar().week.astype(int).to_numpy()
    frame["month"] = frame.index.month
    return frame


def _next_feature_row(history: pd.Series, forecast_date: pd.Timestamp) -> pd.DataFrame:
    future = pd.Series([np.nan], index=pd.DatetimeIndex([forecast_date]), name="demand")
    extended = pd.concat([history.rename("demand"), future])
    return _features(extended).loc[[forecast_date], FEATURES]


def _mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    nonzero = actual != 0
    return float(np.mean(np.abs((actual[nonzero] - predicted[nonzero]) / actual[nonzero])) * 100) if nonzero.any() else 0.0


def forecast_product(
    daily: pd.DataFrame,
    product_id: str,
    model_dir: Path | None = None,
    min_history_days: int = 90,
    validation_days: int = 30,
    horizon_days: int = 90,
) -> ForecastResult:
    """Fit and compare only against a chronological holdout; no random time split."""
    rows = daily.loc[daily["product_id"].astype(str) == str(product_id), ["sales_date", "units_sold"]]
    if rows.empty:
        return ForecastResult(product_id, None, None, [], "No sales history exists for this product.", None)
    rows = rows.groupby("sales_date")["units_sold"].sum().sort_index()
    rows.index = pd.to_datetime(rows.index)
    series = rows.asfreq("D", fill_value=0).astype(float)
    if len(series) < min_history_days:
        return ForecastResult(
            product_id,
            None,
            None,
            [],
            f"Only {len(series)} calendar days of history; at least {min_history_days} are required.",
            None,
        )
    validation_days = min(validation_days, max(7, len(series) // 5))
    train, validation = series.iloc[:-validation_days], series.iloc[-validation_days:]
    train_features = _features(train).dropna()
    actual = validation.to_numpy(dtype=float)
    models = {
        "Random Forest": RandomForestRegressor(n_estimators=100, max_depth=10, min_samples_leaf=2, random_state=42, n_jobs=-1),
        "Gradient Boosting": GradientBoostingRegressor(n_estimators=100, max_depth=2, learning_rate=0.05, loss="huber", random_state=42),
    }
    for model in models.values():
        model.fit(train_features[FEATURES], train_features["demand"])

    scored: list[tuple[str, float, np.ndarray]] = []
    for name in ("Naive", "Moving Average", *models):
        history = train.copy()
        predictions = []
        for validation_date in validation.index:
            if name == "Naive":
                value = float(history.iloc[-1])
            elif name == "Moving Average":
                value = float(history.tail(7).mean())
            else:
                row = _next_feature_row(history, validation_date)
                value = float(models[name].predict(row)[0])
            value = max(0.0, value)
            predictions.append(value)
            history.loc[validation_date] = value
        predicted = np.asarray(predictions, dtype=float)
        scored.append((name, float(mean_absolute_error(actual, predicted)), predicted))
    best_name, _, best_validation = min(scored, key=lambda score: score[1])
    model_metrics = {
        name: {
            "mae": float(mean_absolute_error(actual, prediction)),
            "rmse": float(np.sqrt(mean_squared_error(actual, prediction))),
            "mape_pct": _mape(actual, prediction),
        }
        for name, _, prediction in scored
    }
    residuals = actual - best_validation
    interval = {
        "lower_residual_95": float(np.quantile(residuals, 0.025)),
        "upper_residual_95": float(np.quantile(residuals, 0.975)),
        "validation_days": int(len(residuals)),
        "method": "empirical chronological holdout residual quantiles; approximate",
    }

    final_features = _features(series).dropna()
    model_to_save = None
    if best_name in models:
        model_to_save = models[best_name]
        model_to_save.fit(final_features[FEATURES], final_features["demand"])
    forecasts: list[dict] = []
    history = series.copy()
    future_dates = pd.date_range(series.index[-1] + pd.Timedelta(days=1), periods=horizon_days, freq="D")
    for date in future_dates:
        if best_name == "Naive":
            value = float(history.iloc[-1])
        elif best_name == "Moving Average":
            value = float(history.tail(7).mean())
        else:
            row = _next_feature_row(history, date)
            value = float(model_to_save.predict(row)[0])
        value = max(0.0, value)
        history.loc[date] = value
        forecasts.append(
            {
                "product_id": str(product_id),
                "forecast_date": date.date().isoformat(),
                "predicted_demand": round(value, 3),
                "actual_demand": None,
                "model_name": best_name,
            }
        )
    if model_dir:
        model_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {"model_name": best_name, "estimator": model_to_save, "features": FEATURES, "metrics": model_metrics[best_name]},
            model_dir / f"{product_id}.joblib",
        )
    return ForecastResult(product_id, best_name, model_metrics, forecasts, None, interval)
