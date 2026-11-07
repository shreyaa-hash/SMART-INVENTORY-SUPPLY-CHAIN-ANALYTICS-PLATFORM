from __future__ import annotations

import numpy as np
import pandas as pd


def safe_ratio(numerator: float, denominator: float) -> float | None:
    """Return a ratio if the denominator is finite and non-zero; otherwise return None."""
    if not np.isfinite(denominator) or denominator == 0:
        return None
    value = numerator / denominator
    return float(value) if np.isfinite(value) else None


def inventory_turnover(cogs: float, average_inventory_value: float) -> float | None:
    """Return COGS divided by the period-average inventory value.

    The caller is responsible for passing the average inventory value over the same
    period as the COGS measure; if only a synthetic snapshot exists, this should be
    labeled as an estimate/proxy rather than actual average inventory.
    """
    return safe_ratio(cogs, average_inventory_value)


def days_inventory_outstanding(average_inventory_value: float, cogs: float, days: int) -> float | None:
    """Return the average number of days inventory is held, using the same period basis."""
    ratio = safe_ratio(average_inventory_value * days, cogs)
    return ratio


def stock_coverage_days(quantity_on_hand: float, daily_demand: float) -> float | None:
    """Days of cover based on a daily-demand estimate. Return None for zero demand or invalid data."""
    if not np.isfinite(quantity_on_hand) or not np.isfinite(daily_demand):
        return None
    if quantity_on_hand < 0 or daily_demand < 0:
        raise ValueError("Stock and daily demand must be non-negative.")
    if daily_demand == 0:
        return None
    return float(quantity_on_hand / daily_demand)


def stockout_rate(stockout_events: int, demand_events: int) -> float | None:
    """Observed stockout rate. For synthetic inventory snapshots, prefer a proxy label."""
    ratio = safe_ratio(stockout_events, demand_events)
    return ratio * 100 if ratio is not None else None


def sell_through_rate(units_sold: float, units_available: float) -> float | None:
    """Sold units divided by units available within the selected period."""
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
        "inventory_value_estimated": value,
        "average_inventory_value_estimated": value,
        "inventory_turnover_estimated": inventory_turnover(cogs, value),
        "days_inventory_outstanding_estimated": days_inventory_outstanding(value, cogs, days),
        "sell_through_rate_pct": sell_through_rate(units, units + stock),
        "gross_profit_estimated": gross_profit(revenue, cogs),
        "holding_cost_estimated_annual": inventory_holding_cost(value, 0.25),
    }
