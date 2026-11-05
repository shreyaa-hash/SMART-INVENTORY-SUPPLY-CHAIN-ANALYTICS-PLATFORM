import pandas as pd

from src.recommendations.engine import generate_recommendations


def test_low_stock_recommendation_is_critical_and_explained():
    dates = pd.date_range("2024-01-01", periods=120)
    sales = pd.DataFrame({"product_id": ["P1"] * len(dates), "sales_date": dates, "units_sold": [5] * len(dates)})
    inventory = pd.DataFrame(
        [{"product_id": "P1", "product_name": "Widget", "quantity_on_hand": 0, "data_source": "synthetic"}]
    )
    results = generate_recommendations(inventory, sales, minimum_history_days=90)
    assert results[0]["priority"] == "Critical"
    assert results[0]["reorder_point"] > 0
    assert results[0]["recommended_reorder_quantity"] > 0
    assert results[0]["data_source"] == "synthetic"


def test_synthetic_supplier_risk_is_reported_without_inventing_stock():
    inventory = pd.DataFrame(
        [{"product_id": "P1", "product_name": "Widget", "quantity_on_hand": 20, "data_source": "synthetic"}]
    )
    suppliers = pd.DataFrame(
        [{
            "supplier_id": "SUP-1",
            "supplier_name": "Demo supplier",
            "average_lead_time_days": 10,
            "lead_time_std_days": 3,
            "on_time_delivery_pct": 50,
            "data_source": "synthetic",
        }]
    )
    results = generate_recommendations(
        inventory,
        pd.DataFrame(columns=["product_id", "sales_date", "units_sold"]),
        suppliers,
    )
    supplier_alert = next(item for item in results if item["recommendation_type"] == "supplier_risk")
    assert supplier_alert["current_stock"] is None
    assert supplier_alert["priority"] == "High"
