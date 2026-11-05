from __future__ import annotations

import numpy as np
import pandas as pd


def safe_ratio(numerator: float, denominator: float) -> float | None:
    if not np.isfinite(denominator) or denominator == 0:
        return None
    value = numerator / denominator
    return float(value) if np.isfinite(value) else None


def inventory_turnover(cogs: float, average_inventory_value: float) -> float | None:
    return safe_ratio(cogs, average_inventory_value)


def days_inventory_outstanding(average_inventory_value: float, cogs: float, days: int) -> float | None:
    ratio = safe_ratio(average_inventory_value * days, cogs)
    return ratio


def stockout_rate(stockout_events: int, demand_events: int) -> float | None:
    ratio = safe_ratio(stockout_events, demand_events)
    return ratio * 100 if ratio is not None else None


def sell_through_rate(units_sold: float, units_available: float) -> float | None:
    ratio = safe_ratio(units_sold, units_available)
    return ratio * 100 if ratio is not None else None


def gross_profit(revenue: float, cogs: float) -> float | None:
    if not np.isfinite(revenue) or not np.isfinite(cogs):
        return None
    return float(revenue - cogs)


def reorder_point(
    average_daily_demand: float,
    lead_time_days: float,
    safety_stock: float,
) -> float | None:
    if not all(np.isfinite(value) for value in (average_daily_demand, lead_time_days, safety_stock)):
        return None
    if min(average_daily_demand, lead_time_days, safety_stock) < 0:
        raise ValueError("Demand, lead time, and safety stock cannot be negative.")
    return max(0.0, average_daily_demand * lead_time_days + safety_stock)


def safety_stock(
    demand_std: float,
    lead_time_days: float,
    average_daily_demand: float,
    lead_time_std: float,
    service_z: float = 1.65,
    sufficient_history: bool = True,
) -> float | None:
    values = (demand_std, lead_time_days, average_daily_demand, lead_time_std, service_z)
    if not sufficient_history or not all(np.isfinite(value) for value in values):
        return None
    if min(values) < 0:
        raise ValueError("Demand, lead time, variability, and service factor cannot be negative.")
    demand_variance = lead_time_days * demand_std**2
    lead_variance = average_daily_demand**2 * lead_time_std**2
    return float(service_z * np.sqrt(demand_variance + lead_variance))


def inventory_holding_cost(average_inventory_value: float, annual_holding_rate: float) -> float | None:
    if not np.isfinite(average_inventory_value) or not np.isfinite(annual_holding_rate):
        return None
    return float(max(average_inventory_value, 0) * max(annual_holding_rate, 0))


def abc_classification(consumption_value: pd.Series) -> pd.Series:
    if consumption_value.empty:
        return pd.Series(dtype="object")
    positive = consumption_value.clip(lower=0).sort_values(ascending=False)
    total = positive.sum()
    if total <= 0:
        return pd.Series("C", index=consumption_value.index, dtype="object")
    cumulative = positive.cumsum() / total
    ranked = pd.Series(
        np.select([cumulative <= 0.80, cumulative <= 0.95], ["A", "B"], default="C"),
        index=positive.index,
    )
    return ranked.reindex(consumption_value.index)


def xyz_classification(daily_demand: pd.DataFrame) -> pd.Series:
    if daily_demand.empty:
        return pd.Series(dtype="object")
    cv = daily_demand.std(axis=1, ddof=0).div(daily_demand.mean(axis=1).replace(0, np.nan))
    return pd.cut(cv, bins=[-np.inf, 0.5, 1.0, np.inf], labels=["X", "Y", "Z"]).astype("object").fillna("Z")


def inventory_metrics(inventory: pd.DataFrame, sales: pd.DataFrame, days: int = 365) -> dict:
    stock = float(inventory["quantity_on_hand"].sum()) if not inventory.empty else 0
    value = float(inventory["inventory_value"].sum()) if "inventory_value" in inventory and not inventory.empty else 0
    units = float(sales["units_sold"].sum()) if not sales.empty else 0
    revenue = float(sales["revenue"].sum()) if not sales.empty else 0
    cogs = float(sales["estimated_cogs"].sum()) if "estimated_cogs" in sales and not sales.empty else 0
    return {
        "available_stock": int(stock),
        "inventory_value": value,
        "inventory_turnover": inventory_turnover(cogs, value),
        "days_inventory_outstanding": days_inventory_outstanding(value, cogs, days),
        "sell_through_rate_pct": sell_through_rate(units, units + stock),
        "gross_profit_estimated": gross_profit(revenue, cogs),
        "holding_cost_estimated_annual": inventory_holding_cost(value, 0.25),
    }
