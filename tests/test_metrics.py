import pandas as pd
import numpy as np
import pytest

from src.analytics.metrics import (
    abc_classification,
    days_inventory_outstanding,
    gross_profit,
    inventory_turnover,
    reorder_point,
    safety_stock,
    sell_through_rate,
    stockout_rate,
)


def test_inventory_metrics_handle_zero_denominators():
    assert inventory_turnover(10, 0) is None
    assert days_inventory_outstanding(10, 0, 365) is None
    assert stockout_rate(1, 0) is None
    assert sell_through_rate(10, 0) is None
    assert gross_profit(float("nan"), 10) is None
    assert safety_stock(np.nan, 10, 4, 1) is None


def test_inventory_metrics_calculate_expected_values():
    assert inventory_turnover(200, 100) == 2
    assert days_inventory_outstanding(100, 200, 365) == 182.5
    assert stockout_rate(2, 20) == 10
    assert sell_through_rate(25, 100) == 25
    assert gross_profit(100, 60) == 40
    assert reorder_point(4, 10, 8) == 48
    assert safety_stock(2, 10, 4, 1, sufficient_history=True) > 0
    assert safety_stock(2, 10, 4, 1, sufficient_history=False) is None


def test_abc_classification_uses_cumulative_value():
    result = abc_classification(pd.Series({"large": 80, "medium": 15, "small": 5}))
    assert result["large"] == "A"
    assert result["medium"] == "B"
    assert result["small"] == "C"
