import pandas as pd

from src.analytics.customer_segmentation import (
    assign_customer_segments,
    build_customer_segment_report,
    compute_rfm,
    score_rfm,
)


def _sample_transactions() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"customer_id": 101, "invoice_id": "INV-1", "invoice_date": "2024-01-01", "quantity": 20, "unit_price": 40.0},
            {"customer_id": 101, "invoice_id": "INV-2", "invoice_date": "2024-01-05", "quantity": 20, "unit_price": 45.0},
            {"customer_id": 101, "invoice_id": "INV-3", "invoice_date": "2024-01-09", "quantity": 14, "unit_price": 45.0},
            {"customer_id": 102, "invoice_id": "INV-4", "invoice_date": "2023-12-01", "quantity": 2, "unit_price": 40.0},
            {"customer_id": 102, "invoice_id": "INV-5", "invoice_date": "2023-12-15", "quantity": 1, "unit_price": 50.0},
            {"customer_id": 103, "invoice_id": "INV-6", "invoice_date": "2024-01-30", "quantity": 1, "unit_price": 80.0},
            {"customer_id": None, "invoice_id": "INV-7", "invoice_date": "2024-01-09", "quantity": 4, "unit_price": 10.0},
        ]
    )


def test_compute_rfm_uses_reference_date_and_excludes_missing_customer_ids():
    transactions = _sample_transactions()
    rfm = compute_rfm(transactions, reference_date=pd.Timestamp("2024-01-31"))

    customer_101 = rfm[rfm["customer_id"] == 101].iloc[0]
    customer_102 = rfm[rfm["customer_id"] == 102].iloc[0]

    assert list(rfm["customer_id"]) == [101, 102, 103]
    assert customer_101["recency_days"] == 22
    assert customer_101["frequency"] == 3
    assert customer_101["monetary"] == 2330.0
    assert customer_102["recency_days"] == 47
    assert customer_102["frequency"] == 2
    assert customer_102["monetary"] == 130.0
    assert rfm["customer_id"].isna().sum() == 0


def test_segment_assignment_uses_configurable_thresholds_and_valid_segment_names():
    rfm = pd.DataFrame(
        [
            {"customer_id": 1, "recency_days": 10, "frequency": 6, "monetary": 4000},
            {"customer_id": 2, "recency_days": 50, "frequency": 2, "monetary": 300},
            {"customer_id": 3, "recency_days": 140, "frequency": 1, "monetary": 80},
            {"customer_id": 4, "recency_days": 210, "frequency": 0, "monetary": 0},
        ]
    )
    scored = score_rfm(rfm)
    segmented = assign_customer_segments(scored)

    assert set(segmented["segment"]) <= {
        "Champions",
        "Loyal Customers",
        "Potential Loyalists",
        "New Customers",
        "At Risk",
        "Hibernating",
        "Lost Customers",
    }
    assert segmented.loc[segmented["customer_id"] == 1, "segment"].item() == "Champions"
    assert segmented.loc[segmented["customer_id"] == 3, "segment"].item() == "Hibernating"
    assert segmented.loc[segmented["customer_id"] == 4, "segment"].item() == "Lost Customers"


def test_customer_segment_report_contains_summary_metrics():
    report = build_customer_segment_report(_sample_transactions())

    assert report["summary"]["total_identifiable_customers"] == 3
    assert report["summary"]["repeat_customer_rate"] > 0
    assert report["summary"]["average_customer_monetary_value"] > 0
    assert report["summary"]["purchase_frequency"] > 0
    assert sum(report["segment_counts"].values()) == 3
    assert report["segment_counts"].get("Champions", 0) >= 1
