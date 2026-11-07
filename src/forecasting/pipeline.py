from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

FEATURES = [
    "lag_1", "lag_7", "lag_14", "rolling_7", "rolling_28",
    "day_of_week", "day_of_month", "week_of_year", "month",
]
MODEL_ORDER = ("Naive", "Moving Average", "Seasonal Naive", "Random Forest", "Gradient Boosting")


@dataclass
class ForecastResult:
    product_id: str
    model_name: str | None
    metrics: dict[str, dict[str, float | None]] | None
    forecasts: list[dict]
    warning: str | None
    uncertainty: dict[str, float] | None
    validation_summary: dict[str, Any] | None = None
    final_test_metrics: dict[str, float | None] | None = None


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


def _mape(actual: np.ndarray, predicted: np.ndarray) -> float | None:
    positive = actual > 0
    if not np.any(positive):
        return None
    return float(np.mean(np.abs((actual[positive] - predicted[positive]) / actual[positive])) * 100)


def _wape(actual: np.ndarray, predicted: np.ndarray) -> float | None:
    actual_abs = np.abs(actual)
    denominator = float(actual_abs.sum())
    if denominator == 0:
        return None
    return float(np.sum(np.abs(actual - predicted)) / denominator * 100)


def _smape(actual: np.ndarray, predicted: np.ndarray) -> float:
    denom = np.abs(actual) + np.abs(predicted)
    zero_mask = denom == 0
    percentage = np.zeros_like(actual, dtype=float)
    non_zero = ~zero_mask
    percentage[non_zero] = 200.0 * np.abs(actual[non_zero] - predicted[non_zero]) / denom[non_zero]
    return float(np.mean(percentage))


def _model_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float | None]:
    return {
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(np.sqrt(mean_squared_error(actual, predicted))),
        "mape_pct": _mape(actual, predicted),
        "wape_pct": _wape(actual, predicted),
        "smape_pct": _smape(actual, predicted),
    }


def _aggregate_window_metrics(metric_rows: list[dict[str, float | None]]) -> dict[str, float | None]:
    aggregated: dict[str, float | None] = {}
    for key in ("mae", "rmse", "mape_pct", "wape_pct", "smape_pct"):
        values = [value for value in (row.get(key) for row in metric_rows) if value is not None and np.isfinite(value)]
        aggregated[key] = float(np.mean(values)) if values else None
    return aggregated


def _predict_baseline(name: str, history: pd.Series, dates: pd.DatetimeIndex) -> np.ndarray:
    predictions: list[float] = []
    history_view = history.copy()
    for date in dates:
        if name == "Naive":
            value = float(history_view.iloc[-1])
        elif name == "Moving Average":
            value = float(history_view.tail(7).mean())
        elif name == "Seasonal Naive":
            same_day = history_view[history_view.index.dayofweek == date.dayofweek]
            value = float(same_day.iloc[-1]) if not same_day.empty else float(history_view.iloc[-1])
        else:
            raise ValueError(f"Unsupported baseline model: {name}")
        value = max(0.0, float(value))
        predictions.append(value)
        history_view.loc[date] = value
    return np.asarray(predictions, dtype=float)


def _predict_ml(model, history: pd.Series, dates: pd.DatetimeIndex) -> np.ndarray:
    predictions: list[float] = []
    history_view = history.copy()
    for date in dates:
        row = _next_feature_row(history_view, date)
        value = float(model.predict(row)[0])
        value = max(0.0, float(value))
        predictions.append(value)
        history_view.loc[date] = value
    return np.asarray(predictions, dtype=float)


def _validation_windows(series: pd.Series) -> list[int]:
    candidate_windows = [14, 21, 28]
    valid = [window for window in candidate_windows if window < len(series)]
    if not valid:
        valid = [max(7, len(series) // 5)]
    return sorted(valid, reverse=True)


def forecast_product(
    daily: pd.DataFrame,
    product_id: str,
    model_dir: Path | None = None,
    min_history_days: int = 90,
    validation_days: int = 30,
    horizon_days: int = 90,
) -> ForecastResult:
    """Chronological forecasting with rolling validation windows and a separate final test period."""
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

    validation_candidates = _validation_windows(series)
    validation_windows = [min(window, max(7, validation_days)) for window in validation_candidates]
    validation_windows = sorted(set(validation_windows), reverse=True)

    base_models = {
        "Random Forest": RandomForestRegressor(n_estimators=200, max_depth=8, min_samples_leaf=2, random_state=42, n_jobs=-1),
        "Gradient Boosting": GradientBoostingRegressor(n_estimators=200, max_depth=2, learning_rate=0.05, loss="huber", random_state=42),
    }
    all_models = ("Naive", "Moving Average", "Seasonal Naive", *base_models)
    model_window_scores: dict[str, list[dict[str, float | None]]] = {name: [] for name in all_models}

    for window in validation_windows:
        train_end = len(series) - window
        if train_end <= 0:
            continue
        train = series.iloc[:train_end]
        validation = series.iloc[train_end:]
        train_features = _features(train).dropna()
        if train_features.empty:
            continue
        for name in all_models:
            if name in {"Naive", "Moving Average", "Seasonal Naive"}:
                predictions = _predict_baseline(name, train, validation.index)
            else:
                model = base_models[name].fit(train_features[FEATURES], train_features["demand"])
                predictions = _predict_ml(model, train, validation.index)
            metrics = _model_metrics(validation.to_numpy(dtype=float), predictions)
            model_window_scores[name].append(metrics)

    average_metrics = {
        name: _aggregate_window_metrics(scores)
        for name, scores in model_window_scores.items()
        if scores
    }
    if not average_metrics:
        return ForecastResult(product_id, None, None, [], "Forecast validation failed because there were not enough days to split chronologically.", None)

    candidate_names = ("Naive", "Moving Average", "Random Forest", "Gradient Boosting")
    best_model = min(
        candidate_names,
        key=lambda name: (
            float(average_metrics[name].get("mae") or np.inf),
            float(average_metrics[name].get("rmse") or np.inf),
            float(average_metrics[name].get("wape_pct") or np.inf),
        ),
    )

    final_window = max(14, min(30, len(series) // 6))
    final_train = series.iloc[:-final_window]
    final_test = series.iloc[-final_window:]
    if len(final_train) < min_history_days:
        final_train = series.iloc[:-max(7, final_window // 2)]
        final_test = series.iloc[-max(7, final_window // 2):]

    if best_model in {"Naive", "Moving Average", "Seasonal Naive"}:
        final_predictions = _predict_baseline(best_model, final_train, final_test.index)
    else:
        final_model = base_models[best_model].fit(_features(final_train).dropna()[FEATURES], _features(final_train).dropna()["demand"])
        final_predictions = _predict_ml(final_model, final_train, final_test.index)
    final_metrics = _model_metrics(final_test.to_numpy(dtype=float), final_predictions)
    residuals = final_test.to_numpy(dtype=float) - final_predictions

    uncertainty = {
        "lower_residual_95": float(np.quantile(residuals, 0.025)),
        "upper_residual_95": float(np.quantile(residuals, 0.975)),
        "validation_days": int(len(final_test)),
        "method": "chronological final-test residual quantiles; no leakage and no random split",
    }

    history = series.copy()
    forecasts: list[dict] = []
    future_dates = pd.date_range(series.index[-1] + pd.Timedelta(days=1), periods=horizon_days, freq="D")
    model_to_save = None
    for date in future_dates:
        if best_model in {"Naive", "Moving Average", "Seasonal Naive"}:
            value = _predict_baseline(best_model, history, pd.DatetimeIndex([date]))[0]
        else:
            if model_to_save is None:
                model_to_save = base_models[best_model].fit(_features(series).dropna()[FEATURES], _features(series).dropna()["demand"])
            value = _predict_ml(model_to_save, history, pd.DatetimeIndex([date]))[0]
        value = max(0.0, float(value))
        history.loc[date] = value
        forecasts.append(
            {
                "product_id": str(product_id),
                "forecast_date": date.date().isoformat(),
                "predicted_demand": round(value, 3),
                "actual_demand": None,
                "model_name": best_model,
                "validation_period": f"{final_train.index[0].date()} to {final_test.index[-1].date()}",
                "evaluation_metrics": final_metrics,
                "model_limitations": "Forecasts are generated from recent observed demand and may be unstable if demand is intermittent or zero-inflated.",
            }
        )

    if model_dir:
        model_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {"model_name": best_model, "estimator": model_to_save, "features": FEATURES, "metrics": average_metrics[best_model]},
            model_dir / f"{product_id}.joblib",
        )

    model_metrics = {name: average_metrics[name] for name in candidate_names if name in average_metrics}
    if "Seasonal Naive" in average_metrics:
        seasonal_summary = {"Seasonal Naive": average_metrics["Seasonal Naive"]}
    else:
        seasonal_summary = {}

    return ForecastResult(
        product_id=product_id,
        model_name=best_model,
        metrics=model_metrics,
        forecasts=forecasts,
        warning=None,
        uncertainty=uncertainty,
        validation_summary={
            "validation_windows": validation_windows,
            "final_test_window_days": int(len(final_test)),
            "selection_rule": "Select the model with the lowest average MAE across chronological validation windows and verify it on an untouched final test period.",
            "baseline_models": ["Naive", "Moving Average", "Seasonal Naive"],
            "seasonal_naive_metrics": seasonal_summary,
        },
        final_test_metrics=final_metrics,
    )
