from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from dotenv import load_dotenv

REQUIRED_COLUMNS = {
    "Invoice",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "Price",
    "Country",
}
RANDOM_SEED = 42


def extract_dataset(archive: Path, destination: Path) -> Path:
    """Extract the unchanged UCI workbook from its source archive."""
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as source:
        workbooks = [name for name in source.namelist() if name.lower().endswith(".xlsx")]
        if len(workbooks) != 1:
            raise ValueError(f"Expected one workbook in the UCI archive; found {len(workbooks)}")
        target = destination / "online_retail_II.xlsx"
        with source.open(workbooks[0]) as src, target.open("wb") as dst:
            dst.write(src.read())
    return target


def _category(description: str) -> str:
    text = description.upper()
    rules = {
        "Home & Decor": ("CANDLE", "LIGHT", "LANTERN", "FRAME", "CUSHION", "HOLDER"),
        "Kitchen & Dining": ("MUG", "CUP", "PLATE", "BOWL", "KITCHEN", "CUTLERY"),
        "Gifts & Stationery": ("CARD", "PAPER", "PEN", "GIFT", "WRAP", "NOTEBOOK"),
        "Accessories": ("BAG", "JEWEL", "NECKLACE", "BRACELET", "PURSE", "SCARF"),
        "Toys & Seasonal": ("TOY", "CHRISTMAS", "EASTER", "PARTY", "DECORATION"),
    }
    return next((name for name, tokens in rules.items() if any(token in text for token in tokens)), "General")


def _make_synthetic_entities(
    sales: pd.DataFrame, products: pd.DataFrame, seed: int = RANDOM_SEED
) -> dict[str, pd.DataFrame]:
    """Create reproducible demonstration-only operational records."""
    rng = np.random.default_rng(seed)
    warehouses = pd.DataFrame(
        [
            {"warehouse_id": "WH-01", "warehouse_name": "North Hub", "region": "North", "data_source": "synthetic"},
            {"warehouse_id": "WH-02", "warehouse_name": "Central Hub", "region": "Central", "data_source": "synthetic"},
            {"warehouse_id": "WH-03", "warehouse_name": "South Hub", "region": "South", "data_source": "synthetic"},
            {"warehouse_id": "WH-04", "warehouse_name": "Export Hub", "region": "Export", "data_source": "synthetic"},
        ]
    )
    suppliers = pd.DataFrame(
        [
            {
                "supplier_id": f"SUP-{i:03d}",
                "supplier_name": f"Demonstration Supplier {i:03d}",
                "data_source": "synthetic",
            }
            for i in range(1, 21)
        ]
    )

    product_rows = products.copy()
    product_rows["category_name"] = product_rows["description"].map(_category)
    category_names = sorted(product_rows["category_name"].unique())
    categories = pd.DataFrame(
        [{"category_id": f"CAT-{i:02d}", "category_name": name, "data_source": "synthetic"}
         for i, name in enumerate(category_names, 1)]
    )
    category_ids = dict(zip(categories.category_name, categories.category_id))
    product_rows["category_id"] = product_rows["category_name"].map(category_ids)
    product_rows["supplier_id"] = [
        f"SUP-{i:03d}" for i in rng.integers(1, len(suppliers) + 1, size=len(product_rows))
    ]
    cost_factors = rng.uniform(0.42, 0.72, len(product_rows))
    product_rows["estimated_unit_cost"] = (product_rows["unit_price"] * cost_factors).round(2)
    product_rows["data_source"] = "observed + synthetic cost/category/supplier mapping"
    product_rows = product_rows.drop(columns=["category_name"])

    warehouse_ids = warehouses["warehouse_id"].to_numpy()
    sales_rows = sales.copy()
    invoice_map = pd.DataFrame(
        {
            "invoice_id": sales_rows["invoice_id"].drop_duplicates().to_numpy(),
            "warehouse_id": rng.choice(
                warehouse_ids, size=sales_rows["invoice_id"].nunique()
            ),
        }
    )
    sales_rows = sales_rows.merge(invoice_map, on="invoice_id", how="left", validate="many_to_one")
    sales_rows["warehouse_assignment_source"] = "synthetic"
    sales_rows["sales_date"] = pd.to_datetime(sales_rows["invoice_date"]).dt.normalize()
    orders = (
        sales_rows.groupby("invoice_id", as_index=False)
        .agg(order_date=("invoice_date", "min"), customer_country=("country", "first"))
        .merge(invoice_map, on="invoice_id", how="left")
    )
    orders["data_source"] = "observed transaction; warehouse assignment synthetic"
    sales_rows["order_item_id"] = np.arange(1, len(sales_rows) + 1)
    cost_map = product_rows.set_index("product_id")["estimated_unit_cost"]
    sales_rows["estimated_cogs"] = (
        sales_rows["quantity"] * sales_rows["product_id"].map(cost_map)
    ).round(2)
    order_items = sales_rows[
        ["order_item_id", "invoice_id", "product_id", "quantity", "unit_price", "line_revenue", "estimated_cogs"]
    ].rename(columns={"invoice_id": "order_id"})
    order_items["data_source"] = "observed sales; estimated COGS synthetic"
    daily_sales = (
        sales_rows.groupby(["product_id", "sales_date", "warehouse_id"], as_index=False)
        .agg(
            units_sold=("quantity", "sum"),
            revenue=("line_revenue", "sum"),
            estimated_cogs=("estimated_cogs", "sum"),
        )
    )
    daily_sales["data_source"] = "observed sales; warehouse and COGS synthetic"

    sales_dates = pd.to_datetime(sales["invoice_date"])
    as_of_date = sales_dates.max().normalize()
    product_daily = sales.groupby("product_id").agg(
        demand=("quantity", "sum"), active_days=("invoice_date", "nunique")
    )
    item_cost = product_rows.set_index("product_id")["estimated_unit_cost"]
    inventory_rows: list[dict[str, Any]] = []
    for product_id, row in product_daily.iterrows():
        mean_daily = row["demand"] / max((as_of_date - sales_dates.min().normalize()).days + 1, 1)
        total_stock = max(0, int(np.ceil(mean_daily * rng.uniform(8, 100))))
        allocations = rng.multinomial(total_stock, [0.4, 0.3, 0.2, 0.1])
        for warehouse_id, quantity in zip(warehouse_ids, allocations):
            inventory_rows.append(
                {
                    "product_id": product_id,
                    "warehouse_id": warehouse_id,
                    "quantity_on_hand": int(quantity),
                    "as_of_date": as_of_date.date().isoformat(),
                    "estimated_unit_cost": float(item_cost[product_id]),
                    "data_source": "synthetic demonstration snapshot; not observed stock",
                }
            )
    inventory = pd.DataFrame(inventory_rows)

    delivery_rows: list[dict[str, Any]] = []
    for number in range(1, 401):
        supplier_id = f"SUP-{int(rng.integers(1, len(suppliers) + 1)):03d}"
        ordered = pd.Timestamp("2010-01-01") + pd.Timedelta(days=int(rng.integers(0, 700)))
        lead = int(np.clip(rng.normal(12, 4), 2, 35))
        promised = ordered + pd.Timedelta(days=lead)
        actual = promised + pd.Timedelta(days=int(rng.choice([-3, -2, -1, 0, 0, 1, 2, 4, 7])))
        delivery_rows.append(
            {
                "delivery_id": f"DEL-{number:04d}",
                "supplier_id": supplier_id,
                "order_date": ordered.date().isoformat(),
                "promised_date": promised.date().isoformat(),
                "actual_delivery_date": actual.date().isoformat(),
                "lead_time_days": int((actual - ordered).days),
                "on_time": int(actual <= promised),
                "data_source": "synthetic demonstration delivery",
            }
        )
    return {
        "categories": categories,
        "products": product_rows,
        "warehouses": warehouses,
        "suppliers": suppliers,
        "orders": orders,
        "order_items": order_items,
        "inventory": inventory,
        "supplier_deliveries": pd.DataFrame(delivery_rows),
        "daily_sales": daily_sales,
    }


def process_dataset(
    source_path: Path,
    output_dir: Path,
    sheets: list[str] | None = None,
    seed: int = RANDOM_SEED,
) -> dict[str, Any]:
    """Clean actual retail transactions and export explicitly labeled demo data."""
    frames = pd.read_excel(source_path, sheet_name=sheets or None)
    if isinstance(frames, pd.DataFrame):
        frames = {source_path.stem: frames}
    original = pd.concat(frames.values(), ignore_index=True, sort=False)
    missing_columns = REQUIRED_COLUMNS - set(original.columns)
    if missing_columns:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing_columns)}")

    missing_counts = original.isna().sum().astype(int).to_dict()
    duplicate_count = int(original.duplicated().sum())
    data = original.drop_duplicates().copy()
    data["Invoice"] = data["Invoice"].astype("string").str.strip()
    data["StockCode"] = data["StockCode"].astype("string").str.strip()
    data["Description"] = data["Description"].astype("string").str.strip()
    data["Country"] = data["Country"].astype("string").str.strip()
    data["InvoiceDate"] = pd.to_datetime(data["InvoiceDate"], errors="coerce")
    data["Quantity"] = pd.to_numeric(data["Quantity"], errors="coerce")
    data["Price"] = pd.to_numeric(data["Price"], errors="coerce")

    invalid_date = data["InvoiceDate"].isna()
    invalid_core = (
        data[["Invoice", "StockCode", "Quantity", "Price"]].isna().any(axis=1)
        | data["Invoice"].eq("")
        | data["StockCode"].eq("")
        | data["Quantity"].le(0)
        | data["Price"].le(0)
    )
    cancelled = data["Invoice"].str.startswith("C", na=False)
    invalid_records = int((invalid_date | invalid_core | cancelled).sum())
    cleaned = data.loc[~(invalid_date | invalid_core | cancelled)].copy()
    if cleaned.empty:
        raise ValueError("No valid positive sales remain after cleaning; no processed data was written.")
    cleaned["Description"] = cleaned["Description"].fillna("Unknown product")
    cleaned["Country"] = cleaned["Country"].fillna("Unknown")
    cleaned["line_revenue"] = (cleaned["Quantity"] * cleaned["Price"]).round(2)
    cleaned = cleaned.rename(
        columns={
            "Invoice": "invoice_id",
            "StockCode": "product_id",
            "Description": "description",
            "Quantity": "quantity",
            "InvoiceDate": "invoice_date",
            "Price": "unit_price",
            "Customer ID": "customer_id",
            "Country": "country",
        }
    )
    cleaned["customer_id"] = cleaned.get("customer_id", pd.Series(index=cleaned.index, dtype=float))
    cleaned["invoice_date"] = cleaned["invoice_date"].dt.strftime("%Y-%m-%d %H:%M:%S")
    cleaned["data_source"] = "UCI Online Retail II (observed)"

    products = (
        cleaned.groupby("product_id", as_index=False)
        .agg(description=("description", "first"), unit_price=("unit_price", "median"))
    )
    synthetic = _make_synthetic_entities(cleaned, products, seed)

    output_dir.mkdir(parents=True, exist_ok=True)
    synthetic_dir = output_dir.parent / "synthetic"
    synthetic_dir.mkdir(parents=True, exist_ok=True)
    report_dir = output_dir.parent.parent / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in synthetic.items():
        frame.to_csv(output_dir / f"{name}.csv", index=False)
        if name in {"categories", "warehouses", "suppliers", "inventory", "supplier_deliveries"}:
            frame.to_csv(synthetic_dir / f"{name}.csv", index=False)
    cleaned.to_csv(output_dir / "cleaned_transactions.csv", index=False)

    numeric = original.select_dtypes(include=np.number)
    outliers: dict[str, int] = {}
    for column in numeric.columns:
        values = numeric[column].dropna()
        if len(values):
            q1, q3 = values.quantile([0.25, 0.75])
            spread = q3 - q1
            outliers[column] = int(((values < q1 - 1.5 * spread) | (values > q3 + 1.5 * spread)).sum())
    quality = {
        "dataset": "UCI Online Retail II",
        "dataset_url": "https://archive.ics.uci.edu/dataset/502/online+retail+ii",
        "source_sheets": {name: int(len(frame)) for name, frame in frames.items()},
        "total_source_records": int(len(original)),
        "total_clean_sales_records": int(len(cleaned)),
        "missing_values_by_column": missing_counts,
        "duplicate_count_removed": duplicate_count,
        "invalid_records_excluded": invalid_records,
        "outlier_count_by_numeric_column_iqr_flagged_not_removed": outliers,
        "data_type_summary": {key: str(value) for key, value in original.dtypes.items()},
        "cleaning_actions": [
            "Removed exact duplicate rows",
            "Parsed invoice dates and coerced invalid dates to missing",
            "Excluded cancellations, non-positive quantities/prices, invalid dates, and missing invoice/product keys",
            "Trimmed product, invoice, description, and country strings",
            "Filled missing product descriptions/countries with explicit Unknown labels",
            "Flagged IQR outliers without deleting plausible high-volume sales",
            "Generated synthetic stock, unit costs, categories, warehouses, suppliers, and deliveries with seed 42",
        ],
        "synthetic_data_notice": (
            "Inventory, unit costs, inferred categories, warehouse assignments, suppliers and deliveries "
            "are synthetic demonstration data, not UCI observations."
        ),
    }
    (report_dir / "data_quality.json").write_text(json.dumps(quality, indent=2), encoding="utf-8")
    pd.DataFrame(
        [{"column": name, "missing_values": count} for name, count in missing_counts.items()]
    ).to_csv(report_dir / "missing_values.csv", index=False)
    return quality


if __name__ == "__main__":
    import argparse
    import os

    load_dotenv()
    parser = argparse.ArgumentParser(description="Process the UCI Online Retail II workbook.")
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(os.getenv("DATASET_PATH", "data/raw/online_retail_II.xlsx")),
    )
    parser.add_argument("--output", type=Path, default=Path("data/processed"))
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    args = parser.parse_args()
    sheet_setting = os.getenv("DATASET_SHEETS")
    selected_sheets = [name.strip() for name in sheet_setting.split(",")] if sheet_setting else None
    result = process_dataset(args.source, args.output, sheets=selected_sheets, seed=args.seed)
    print(json.dumps(result, indent=2))
