from __future__ import annotations

from typing import Any

import pandas as pd

DEFAULT_SEGMENT_THRESHOLDS: dict[str, dict[str, float]] = {
    "Champions": {"recency_max": 30, "frequency_min": 3, "monetary_min": 1000.0},
    "Loyal Customers": {"recency_max": 60, "frequency_min": 2, "monetary_min": 500.0},
    "Potential Loyalists": {"recency_max": 90, "frequency_min": 1, "monetary_min": 250.0},
    "New Customers": {"recency_max": 30, "frequency_min": 1, "monetary_min": 0.0},
    "At Risk": {"recency_min": 60, "recency_max": 180, "frequency_max": 2},
    "Hibernating": {"recency_min": 90, "recency_max": 365, "frequency_max": 1},
    "Lost Customers": {"recency_min": 180, "frequency_max": 1},
}


def _normalise_customer_transactions(transactions: pd.DataFrame) -> pd.DataFrame:
    frame = transactions.copy()
    required = {"customer_id", "invoice_id", "invoice_date", "quantity", "unit_price"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Customer segmentation requires columns: {sorted(required)}; missing {missing}")
    frame = frame.loc[frame["customer_id"].notna()].copy()
    if frame.empty:
        return frame
    frame["invoice_date"] = pd.to_datetime(frame["invoice_date"], errors="coerce")
    frame["quantity"] = pd.to_numeric(frame["quantity"], errors="coerce")
    frame["unit_price"] = pd.to_numeric(frame["unit_price"], errors="coerce")
    frame = frame.loc[frame["invoice_date"].notna() & frame["quantity"].gt(0) & frame["unit_price"].ge(0)].copy()
    frame["line_revenue"] = (frame["quantity"] * frame["unit_price"]).round(2)
    frame["customer_id"] = frame["customer_id"].astype(int)
    return frame


def compute_reference_date(transactions: pd.DataFrame) -> pd.Timestamp:
    """Use the latest valid observed transaction in the cleaned dataset as the reference date."""
    normalised = _normalise_customer_transactions(transactions)
    if normalised.empty:
        raise ValueError("Cannot compute a reference date because no valid customer transactions remain.")
    return pd.Timestamp(normalised["invoice_date"].max()).normalize()


def compute_rfm(
    transactions: pd.DataFrame,
    reference_date: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Compute recency, frequency, and monetary summaries per customer.

    Recency is measured as the number of days between the customer's last observed purchase and
    the reference date. Frequency is the number of distinct invoices/orders. Monetary is the sum
    of valid observed transaction revenue.
    """
    frame = _normalise_customer_transactions(transactions)
    if frame.empty:
        return pd.DataFrame(columns=["customer_id", "recency_days", "frequency", "monetary"]).astype({"customer_id": int})
    if reference_date is None:
        reference_date = compute_reference_date(frame)
    reference = pd.Timestamp(reference_date).normalize()
    grouped = (
        frame.groupby("customer_id", as_index=False)
        .agg(
            recency_days=("invoice_date", lambda dates: int((reference - dates.max()).days)),
            frequency=("invoice_id", "nunique"),
            monetary=("line_revenue", "sum"),
        )
        .sort_values(["monetary", "frequency"], ascending=False)
        .reset_index(drop=True)
    )
    grouped["monetary"] = grouped["monetary"].round(2)
    return grouped


def score_rfm(rfm: pd.DataFrame) -> pd.DataFrame:
    """Assign explicit 1-5 scores across the configured business thresholds.

    Methodology:
    - Recency: lower is better, so stronger customers have lower recency. Scores map to
      5: <= 30 days, 4: <= 60 days, 3: <= 90 days, 2: <= 180 days, 1: > 180 days.
    - Frequency and monetary: higher values are better. Scores map to 5 for very strong values,
      4 for strong, 3 for moderate, 2 for low, and 1 for very low.
    """
    if rfm.empty:
        return rfm.copy()
    scored = rfm.copy()
    recency_bins = [30, 60, 90, 180]
    scored["recency_score"] = scored["recency_days"].apply(
        lambda days: 5 if days <= recency_bins[0] else 4 if days <= recency_bins[1] else 3 if days <= recency_bins[2] else 2 if days <= recency_bins[3] else 1
    )
    scored["frequency_score"] = scored["frequency"].apply(
        lambda value: 5 if value >= 5 else 4 if value >= 3 else 3 if value >= 2 else 2 if value >= 1 else 1
    )
    scored["monetary_score"] = scored["monetary"].apply(
        lambda value: 5 if value >= 2000 else 4 if value >= 1000 else 3 if value >= 500 else 2 if value >= 100 else 1
    )
    return scored


def assign_customer_segments(
    rfm: pd.DataFrame,
    thresholds: dict[str, dict[str, float]] | None = None,
) -> pd.DataFrame:
    """Assign each customer to a segment using transparent, configurable thresholds."""
    if rfm.empty:
        return rfm.copy().assign(segment=pd.Series(dtype="object"))
    segment_ranges = thresholds or DEFAULT_SEGMENT_THRESHOLDS
    segments = []
    for row in rfm.to_dict("records"):
        recency = float(row["recency_days"])
        frequency = float(row["frequency"])
        monetary = float(row["monetary"])
        threshold = None
        if (
            recency <= segment_ranges["Champions"].get("recency_max", float("inf"))
            and frequency >= segment_ranges["Champions"].get("frequency_min", 0.0)
            and monetary >= segment_ranges["Champions"].get("monetary_min", 0.0)
        ):
            threshold = "Champions"
        elif (
            recency <= segment_ranges["Loyal Customers"].get("recency_max", float("inf"))
            and frequency >= segment_ranges["Loyal Customers"].get("frequency_min", 0.0)
            and monetary >= segment_ranges["Loyal Customers"].get("monetary_min", 0.0)
        ):
            threshold = "Loyal Customers"
        elif (
            recency <= segment_ranges["Potential Loyalists"].get("recency_max", float("inf"))
            and frequency >= segment_ranges["Potential Loyalists"].get("frequency_min", 0.0)
            and monetary >= segment_ranges["Potential Loyalists"].get("monetary_min", 0.0)
        ):
            threshold = "Potential Loyalists"
        elif (
            recency <= segment_ranges["New Customers"].get("recency_max", float("inf"))
            and frequency >= segment_ranges["New Customers"].get("frequency_min", 0.0)
        ):
            threshold = "New Customers"
        elif (
            recency >= segment_ranges["Lost Customers"].get("recency_min", 0.0)
            and frequency <= segment_ranges["Lost Customers"].get("frequency_max", float("inf"))
        ):
            threshold = "Lost Customers"
        elif (
            segment_ranges["Hibernating"].get("recency_min", 0.0) <= recency <= segment_ranges["Hibernating"].get("recency_max", float("inf"))
            and frequency <= segment_ranges["Hibernating"].get("frequency_max", float("inf"))
        ):
            threshold = "Hibernating"
        elif (
            segment_ranges["At Risk"].get("recency_min", 0.0) <= recency <= segment_ranges["At Risk"].get("recency_max", float("inf"))
            and frequency <= segment_ranges["At Risk"].get("frequency_max", float("inf"))
        ):
            threshold = "At Risk"
        else:
            threshold = "Loyal Customers"
        segments.append(threshold)
    result = rfm.copy()
    result["segment"] = segments
    return result


def summarize_segments(segmented: pd.DataFrame) -> dict[str, Any]:
    """Return both customer-level and segment-level summaries with validation checks."""
    counts = segmented["segment"].value_counts().to_dict() if not segmented.empty else {}
    expected = [
        "Champions",
        "Loyal Customers",
        "Potential Loyalists",
        "New Customers",
        "At Risk",
        "Hibernating",
        "Lost Customers",
    ]
    missing = [name for name in expected if counts.get(name, 0) < 0]
    if missing:
        raise ValueError(f"Unexpected segment count state for: {missing}")
    segment_revenue = (
        segmented.groupby("segment", dropna=False)["monetary"].sum().sort_values(ascending=False).to_dict()
        if not segmented.empty
        else {}
    )
    return {
        "total_identifiable_customers": int(segmented["customer_id"].nunique()) if not segmented.empty else 0,
        "repeat_customer_rate": float((segmented["frequency"] > 1).mean()) if not segmented.empty else 0.0,
        "average_customer_monetary_value": float(segmented["monetary"].mean()) if not segmented.empty else 0.0,
        "purchase_frequency": float(segmented["frequency"].mean()) if not segmented.empty else 0.0,
        "customer_revenue_contribution_pct": float((segmented["monetary"].sum() / segmented["monetary"].sum()) * 100) if not segmented.empty else 0.0,
        "segment_counts": counts,
        "segment_revenue": segment_revenue,
    }


def build_customer_segment_report(
    transactions: pd.DataFrame,
    thresholds: dict[str, dict[str, float]] | None = None,
    reference_date: pd.Timestamp | None = None,
) -> dict[str, Any]:
    """Create a complete customer segmentation report."""
    frame = _normalise_customer_transactions(transactions)
    if frame.empty:
        return {
            "rfm": pd.DataFrame(columns=["customer_id", "recency_days", "frequency", "monetary", "segment"]),
            "segment_counts": {},
            "summary": {
                "total_identifiable_customers": 0,
                "repeat_customer_rate": 0.0,
                "average_customer_monetary_value": 0.0,
                "purchase_frequency": 0.0,
                "customer_revenue_contribution_pct": 0.0,
            },
        }
    rfm = compute_rfm(frame, reference_date=reference_date)
    scores = score_rfm(rfm)
    segmented = assign_customer_segments(scores, thresholds=thresholds)
    summary = summarize_segments(segmented)
    return {
        "rfm": segmented,
        "segment_counts": summary["segment_counts"],
        "summary": {
            "total_identifiable_customers": summary["total_identifiable_customers"],
            "repeat_customer_rate": summary["repeat_customer_rate"],
            "average_customer_monetary_value": summary["average_customer_monetary_value"],
            "purchase_frequency": summary["purchase_frequency"],
            "customer_revenue_contribution_pct": summary["customer_revenue_contribution_pct"],
        },
        "segment_revenue": summary["segment_revenue"],
    }
