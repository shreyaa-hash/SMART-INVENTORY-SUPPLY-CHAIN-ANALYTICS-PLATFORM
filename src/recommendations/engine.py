from __future__ import annotations

import pandas as pd

from src.analytics.metrics import reorder_point, safety_stock


def _priority_order() -> dict[str, int]:
    return {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


def _safe_float(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        number = float(value)
        return number if pd.notna(number) and number != float("inf") else None
    except (TypeError, ValueError):
        return None


def _recommendation_base(product_id: str, product_name: str, *, current_stock: int | None, data_provenance_warning: str) -> dict:
    return {
        "product_id": str(product_id),
        "product_name": str(product_name),
        "current_stock": current_stock,
        "estimated_daily_demand": None,
        "predicted_demand_30d": None,
        "forecast_demand": None,
        "safety_stock": None,
        "reorder_point": None,
        "suggested_reorder_quantity": 0,
        "recommended_reorder_quantity": 0,
        "estimated_stock_coverage": None,
        "inventory_coverage_days": None,
        "reason": "No actionable recommendation available.",
        "priority": "Low",
        "data_provenance_warning": data_provenance_warning,
        "data_source": "unknown",
    }


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
    forecast_data: pd.DataFrame | None = None,
) -> list[dict]:
    """Generate transparent inventory actions using observed demand with synthetic inventory context."""
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
    if supplier_performance is not None and not supplier_performance.empty:
        performance = supplier_performance.set_index("supplier_id")
        leads = performance["average_lead_time_days"].to_dict()
        if "lead_time_std_days" in performance:
            lead_variability = performance["lead_time_std_days"].to_dict()

    forecast_map: dict[str, float | None] = {}
    if forecast_data is not None and not forecast_data.empty:
        if "predicted_demand" in forecast_data.columns:
            forecast_map = forecast_data.groupby("product_id")["predicted_demand"].mean().to_dict()
        elif "forecast_demand" in forecast_data.columns:
            forecast_map = forecast_data.groupby("product_id")["forecast_demand"].mean().to_dict()

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
        product_id = str(row.get("product_id", ""))
        if not product_id:
            continue
        product_name = str(row.get("product_name", product_id))
        stock_value = row.get("quantity_on_hand")
        stock = int(float(stock_value)) if stock_value is not None and pd.notna(stock_value) else None
        if stock is None:
            rec = _recommendation_base(
                product_id,
                product_name,
                current_stock=None,
                data_provenance_warning="Synthetic inventory snapshot is missing; recommendation is based on available demand estimates only.",
            )
            rec["reason"] = "Inventory is missing, so no reorder recommendation can be generated from observed stock levels."
            rec["priority"] = "Medium"
            rec["estimated_daily_demand"] = None
            rec["predicted_demand_30d"] = None
            rec["forecast_demand"] = forecast_map.get(product_id)
            rec["suggested_reorder_quantity"] = 0
            rec["recommended_reorder_quantity"] = 0
            rec["data_source"] = str(row.get("data_source", "synthetic"))
            recommendations.append(rec)
            continue

        history = (
            all_product.get_group(product_id).set_index("sales_date")["units_sold"]
            if product_id in all_product.groups
            else pd.Series(dtype=float)
        )
        start = today - pd.Timedelta(days=89)
        recent_index = pd.date_range(start, today, freq="D")
        recent_history = history.reindex(recent_index, fill_value=0) if not history.empty else pd.Series(0.0, index=recent_index)

        first_date = (history_start_dates or {}).get(product_id)
        if first_date is None and not history.empty:
            first_date = history.index.min()
        history_days = int((today - pd.Timestamp(first_date).normalize()).days + 1) if first_date is not None else 0
        demand_observed = history_days >= minimum_history_days
        mean_daily = float(recent_history.mean()) if demand_observed and not recent_history.empty else 0.0
        demand_std = float(recent_history.std(ddof=0)) if demand_observed and not recent_history.empty else 0.0

        lead = float(leads.get(row.get("supplier_id"), 14.0))
        lead_std = float(lead_variability.get(row.get("supplier_id"), 0.0))
        buffer = safety_stock(demand_std, lead, mean_daily, lead_std, service_z, sufficient_history=demand_observed)
        safety_stock_value = float(buffer) if buffer is not None else 0.0
        point = reorder_point(mean_daily, lead, safety_stock_value)
        coverage = stock / mean_daily if mean_daily > 0 else float("inf")
        forecast_value = forecast_map.get(product_id)
        if forecast_value is None and demand_observed:
            forecast_value = mean_daily

        reason = "No specific action required."
        priority = "Low"
        if mean_daily > 0 and stock <= (point or 0):
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

        if mean_daily == 0 and forecast_value is None:
            reason = "No recent demand history or forecast exists; inventory should be reviewed before replenishment."
            priority = "Medium"

        suggested_quantity = max(0, int(round((mean_daily * target_coverage_days) - stock)))
        if forecast_value is not None and forecast_value > 0:
            suggested_quantity = max(suggested_quantity, int(round(forecast_value * target_coverage_days / 30 - stock)))

        if coverage == float("inf"):
            coverage_label = None
        else:
            coverage_label = round(float(coverage), 1) if pd.notna(coverage) else None

        rec = {
            "product_id": product_id,
            "product_name": product_name,
            "current_stock": stock,
            "estimated_daily_demand": round(mean_daily, 2) if mean_daily else (None if not demand_observed else 0.0),
            "predicted_demand_30d": round((mean_daily or 0.0) * 30, 2) if (mean_daily or 0.0) > 0 else None,
            "forecast_demand": round(float(forecast_value), 2) if forecast_value is not None else None,
            "safety_stock": round(safety_stock_value, 2) if safety_stock_value else 0.0,
            "reorder_point": round(float(point), 2) if point is not None else None,
            "suggested_reorder_quantity": max(0, suggested_quantity),
            "recommended_reorder_quantity": max(0, suggested_quantity),
            "estimated_stock_coverage": coverage_label,
            "inventory_coverage_days": coverage_label,
            "reason": reason,
            "priority": priority,
            "estimated_lead_time_days": round(float(lead), 2) if lead is not None else None,
            "data_source": str(row.get("data_source", "synthetic")),
            "data_provenance_warning": "Synthetic inventory and forecast values are demonstration estimates, not observed business records.",
        }
        if reason == "No specific action required.":
            rec["priority"] = "Low"
        recommendations.append(rec)

    if supplier_performance is not None and not supplier_performance.empty:
        for supplier in supplier_performance.to_dict("records"):
            reliability_pct = _safe_float(supplier.get("on_time_delivery_pct", 100.0))
            if reliability_pct is None:
                continue
            if reliability_pct < supplier_on_time_threshold_pct:
                rec = _recommendation_base(
                    str(supplier.get("supplier_id", "SUP-UNKNOWN")),
                    str(supplier.get("supplier_name", supplier.get("supplier_id", "Unknown supplier"))),
                    current_stock=None,
                    data_provenance_warning="Synthetic supplier delivery performance is a demonstration estimate only; actual supplier history is unavailable.",
                )
                rec["recommendation_type"] = "supplier_risk"
                rec["reason"] = (
                    f"Synthetic supplier on-time rate is {reliability_pct:.1f}%, below the configured "
                    f"{supplier_on_time_threshold_pct:.1f}% threshold."
                )
                rec["priority"] = "High" if reliability_pct < 60 else "Medium"
                rec["estimated_daily_demand"] = None
                rec["predicted_demand_30d"] = None
                rec["forecast_demand"] = None
                rec["safety_stock"] = None
                rec["reorder_point"] = None
                rec["suggested_reorder_quantity"] = 0
                rec["recommended_reorder_quantity"] = 0
                rec["estimated_stock_coverage"] = None
                rec["inventory_coverage_days"] = None
                rec["data_source"] = str(supplier.get("data_source", "synthetic demonstration deliveries"))
                recommendations.append(rec)

    order = _priority_order()
    return sorted(recommendations, key=lambda item: (order.get(item["priority"], 99), item["product_name"]))
