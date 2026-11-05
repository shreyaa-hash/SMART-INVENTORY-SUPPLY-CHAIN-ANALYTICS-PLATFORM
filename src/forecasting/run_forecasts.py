from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.forecasting.pipeline import forecast_product


def run_batch(
    processed_dir: Path = Path("data/processed"),
    model_dir: Path = Path("models"),
    report_dir: Path = Path("reports"),
    product_limit: int = 10,
) -> dict:
    daily = pd.read_csv(
        processed_dir / "daily_sales.csv",
        parse_dates=["sales_date"],
        dtype={"product_id": str},
        low_memory=False,
    )
    top_ids = (
        daily.groupby("product_id").units_sold.sum().nlargest(product_limit).index.astype(str).tolist()
    )
    names = pd.read_csv(processed_dir / "products.csv", dtype={"product_id": str}).set_index("product_id").description.to_dict()
    outputs = []
    evaluation = {}
    warnings = []
    for product_id in top_ids:
        result = forecast_product(daily, product_id, model_dir, horizon_days=90)
        if result.warning:
            warnings.append({"product_id": product_id, "warning": result.warning})
            continue
        outputs.extend(result.forecasts)
        evaluation[product_id] = {
            "product_name": names.get(product_id, product_id),
            "selected_model": result.model_name,
            "validation_metrics": result.metrics,
            "uncertainty": result.uncertainty,
        }
    model_names = ("Naive", "Moving Average", "Random Forest", "Gradient Boosting")
    model_summary = {}
    for model_name in model_names:
        scores = [
            item["validation_metrics"][model_name]
            for item in evaluation.values()
        ]
        model_summary[model_name] = {
            metric: sum(score[metric] for score in scores) / len(scores)
            for metric in ("mae", "rmse", "mape_pct")
        } if scores else None
    selected_counts = {
        model_name: sum(item["selected_model"] == model_name for item in evaluation.values())
        for model_name in model_names
    }
    processed_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(outputs).to_csv(processed_dir / "forecasts.csv", index=False)
    report_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "source": "UCI Online Retail II observed transactions",
        "selection": f"Top {product_limit} products by observed historical units",
        "evaluation": evaluation,
        "mean_validation_metrics_across_evaluated_products": model_summary,
        "selected_model_counts": selected_counts,
        "warnings": warnings,
        "forecast_note": "Future actual demand is unavailable; actual_demand is null.",
    }
    (report_dir / "model_evaluation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(run_batch(), indent=2))
