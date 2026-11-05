import numpy as np
import pandas as pd

from src.forecasting.pipeline import forecast_product


def test_forecast_requires_sufficient_history():
    frame = pd.DataFrame(
        {"product_id": ["P1"] * 20, "sales_date": pd.date_range("2020-01-01", periods=20), "units_sold": [2] * 20}
    )
    result = forecast_product(frame, "P1", min_history_days=90)
    assert result.warning
    assert result.forecasts == []


def test_forecast_uses_chronological_evaluation_and_saves_model(tmp_path):
    dates = pd.date_range("2020-01-01", periods=160)
    frame = pd.DataFrame(
        {"product_id": ["P1"] * len(dates), "sales_date": dates, "units_sold": 3 + np.arange(len(dates)) % 4}
    )
    result = forecast_product(frame, "P1", tmp_path, horizon_days=30, min_history_days=90, validation_days=21)
    assert result.warning is None
    assert result.model_name in {"Naive", "Moving Average", "Random Forest", "Gradient Boosting"}
    assert set(result.metrics) == {"Naive", "Moving Average", "Random Forest", "Gradient Boosting"}
    assert len(result.forecasts) == 30
    assert result.forecasts[0]["forecast_date"] == (dates[-1] + pd.Timedelta(days=1)).date().isoformat()
    assert all(row["predicted_demand"] >= 0 and row["actual_demand"] is None for row in result.forecasts)
    assert (tmp_path / "P1.joblib").exists()
