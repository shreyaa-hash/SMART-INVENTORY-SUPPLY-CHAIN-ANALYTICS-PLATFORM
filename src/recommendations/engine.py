from __future__ import annotations

import pandas as pd

from src.analytics.metrics import reorder_point, safety_stock


def generate_recommendations(
    inventory: pd.DataFrame,
    daily_sales: pd.DataFrame,
    supplier_performance: pd.DataFrame | None = None,
    *,
    target_coverage_days: int = 45,
    stock_multiplier: float = 1.5,
    service_z: float = 1.65,
    minimum_history_days: int = 90,
    supplier_on_time_threshold_pct: float = 80.0,
    history_start_dates: dict[str, object] | None = None,
    low_stock_coverage_days: int = 14,
    stockout_risk_coverage_days: int = 30,
    slow_moving_days: int = 90,
    dead_stock_days: int = 180,
) -> list[dict]:
    """Generate transparent inventory actions; stock inputs may be synthetic demo data."""
    if inventory.empty:
        return []
    daily = daily_sales.copy()
    if daily.empty:
        daily = pd.DataFrame(columns=["product_id", "sales_date", "units_sold"])
    else:
        daily["sales_date"] = pd.to_datetime(daily["sales_date"])
        daily = daily.groupby(["product_id", "sales_date"], as_index=False).units_sold.sum()
    today = daily["sales_date"].max().normalize() if not daily.empty else pd.Timestamp.today().normalize()
    all_product = daily.groupby("product_id")
    leads = {}
    lead_variability = {}
    reliability = {}
    if supplier_performance is not None and not supplier_performance.empty:
        performance = supplier_performance.set_index("supplier_id")
        leads = performance["average_lead_time_days"].to_dict()
        if "lead_time_std_days" in performance:
            lead_variability = performance["lead_time_std_days"].to_dict()
        if "on_time_delivery_pct" in performance:
            reliability = performance["on_time_delivery_pct"].to_dict()
    if "last_sale" in inventory:
        joined = inventory.copy()
    else:
        joined = inventory.merge(
            daily.groupby("product_id", as_index=False).agg(last_sale=("sales_date", "max")),
            on="product_id",
            how="left",
        )
    recommendations: list[dict] = []
    for row in joined.to_dict("records"):
        product_id = str(row["product_id"])
        history = (
            all_product.get_group(product_id).set_index("sales_date")["units_sold"]
            if product_id in all_product.groups
            else pd.Series(dtype=float)
        )
        stock = int(row["quantity_on_hand"])
        start = today - pd.Timedelta(days=89)
        recent_index = pd.date_range(start, today, freq="D")
        recent_history = history.reindex(recent_index, fill_value=0) if not history.empty else pd.Series(0.0, index=recent_index)
        first_date = (history_start_dates or {}).get(product_id)
        if first_date is None and not history.empty:
            first_date = history.index.min()
        history_days = int((today - pd.Timestamp(first_date).normalize()).days + 1) if first_date is not None else 0
        demand_observed = history_days >= minimum_history_days
        mean_daily = float(recent_history.mean()) if demand_observed else 0.0
        demand_std = float(recent_history.std(ddof=0)) if demand_observed else 0.0
        lead = float(leads.get(row.get("supplier_id"), 14.0))
        lead_std = float(lead_variability.get(row.get("supplier_id"), 0.0))
        buffer = safety_stock(
            demand_std, lead, mean_daily, lead_std, service_z,
            sufficient_history=demand_observed,
        )
        if buffer is None:
            buffer = 0.0
        point = reorder_point(mean_daily, lead, buffer)
        coverage = stock / mean_daily if mean_daily > 0 else float("inf")
        reason = None
        priority = "Low"
        if mean_daily > 0 and stock <= point:
            reason = "Available stock is at or below the calculated reorder point."
            priority = "Critical" if stock <= mean_daily * lead * 0.5 else "High"
        elif mean_daily > 0 and stock <= mean_daily * low_stock_coverage_days:
            reason = f"Estimated coverage is at or below the configured {low_stock_coverage_days}-day low-stock threshold."
            priority = "High"
        elif mean_daily > 0 and coverage > target_coverage_days * stock_multiplier:
            reason = f"Estimated inventory coverage ({coverage:.0f} days) exceeds the configured target."
            priority = "Medium"
        elif mean_daily == 0 and row.get("last_sale") is not None and (today - pd.Timestamp(row["last_sale"])).days >= dead_stock_days:
            reason = f"No demand in the recent window and last observed sale was at least {dead_stock_days} days ago."
            priority = "Medium"
        elif mean_daily == 0 and row.get("last_sale") is not None and (today - pd.Timestamp(row["last_sale"])).days >= slow_moving_days:
            reason = f"No demand in the recent 90-day window; last sale was at least {slow_moving_days} days ago."
            priority = "Low"
        elif mean_daily > 0 and stock < mean_daily * stockout_risk_coverage_days:
            reason = f"Current stock is below the next {stockout_risk_coverage_days} days of recent average demand."
            priority = "High"
        elif demand_observed and len(recent_history) >= 60:
            recent_30 = float(recent_history.tail(30).mean())
            preceding_30 = float(recent_history.iloc[-60:-30].mean())
            if preceding_30 > 0 and recent_30 >= preceding_30 * 1.2:
                reason = "Daily demand increased by at least 20% versus the preceding 30-day window."
                priority = "Medium"
        if reason:
            recommendations.append(
                {
                    "product_id": product_id,
                    "product_name": str(row.get("product_name", product_id)),
                    "current_stock": stock,
                    "predicted_demand_30d": round(mean_daily * 30, 2),
                    "reorder_point": round(point, 2),
                    "recommended_reorder_quantity": max(0, int(round(mean_daily * target_coverage_days - stock))),
                    "inventory_coverage_days": None if coverage == float("inf") else round(coverage, 1),
                    "reason": reason,
                    "priority": priority,
                    "data_source": str(row.get("data_source", "unknown")),
                }
            )
    if supplier_performance is not None and not supplier_performance.empty:
        for supplier in supplier_performance.to_dict("records"):
            reliability_pct = float(supplier.get("on_time_delivery_pct", 100.0))
            if reliability_pct < supplier_on_time_threshold_pct:
                recommendations.append(
                    {
                        "product_id": str(supplier["supplier_id"]),
                        "product_name": str(supplier.get("supplier_name", supplier["supplier_id"])),
                        "recommendation_type": "supplier_risk",
                        "current_stock": None,
                        "predicted_demand_30d": None,
                        "reorder_point": None,
                        "recommended_reorder_quantity": 0,
                        "inventory_coverage_days": None,
                        "reason": (
                            f"Synthetic supplier on-time rate is {reliability_pct:.1f}%, below the "
                            f"configured {supplier_on_time_threshold_pct:.1f}% threshold."
                        ),
                        "priority": "High" if reliability_pct < 60 else "Medium",
                        "data_source": str(supplier.get("data_source", "synthetic demonstration deliveries")),
                    }
                )
    order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    return sorted(recommendations, key=lambda item: (order[item["priority"]], item["product_name"]))
