from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sqlalchemy import insert

from src.database.connection import get_engine
from src.database.models import (
    Base, Category, DailySale, Inventory, Order, OrderItem, Product,
    Supplier, SupplierDelivery, Warehouse,
)

TABLES = {
    "categories": Category,
    "suppliers": Supplier,
    "warehouses": Warehouse,
    "products": Product,
    "orders": Order,
    "order_items": OrderItem,
    "inventory": Inventory,
    "supplier_deliveries": SupplierDelivery,
    "daily_sales": DailySale,
}


def _records(name: str, csv_path: Path) -> list[dict]:
    frame = pd.read_csv(
        csv_path,
        dtype={
            column: str
            for column in (
                "product_id", "order_id", "invoice_id", "warehouse_id",
                "supplier_id", "category_id", "delivery_id",
            )
        },
        low_memory=False,
    )
    if name == "products":
        frame = frame.rename(columns={"description": "description"})
    elif name == "orders":
        frame = frame.rename(columns={"invoice_id": "order_id"})
        if "customer_id" in frame.columns:
            frame["customer_id"] = pd.to_numeric(frame["customer_id"], errors="coerce")
        frame["order_date"] = pd.to_datetime(frame["order_date"])
    elif name == "order_items":
        frame["order_item_id"] = frame["order_item_id"].astype(int)
    elif name == "inventory":
        frame["as_of_date"] = pd.to_datetime(frame["as_of_date"]).dt.date
    elif name == "supplier_deliveries":
        for column in ("order_date", "promised_date", "actual_delivery_date"):
            frame[column] = pd.to_datetime(frame[column]).dt.date
    elif name == "daily_sales":
        frame["sales_date"] = pd.to_datetime(frame["sales_date"]).dt.date
    return frame.where(pd.notna(frame), None).to_dict(orient="records")


def load_processed_data(data_dir: Path, database_url: str | None = None) -> dict[str, int]:
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
    counts: dict[str, int] = {}
    with engine.begin() as connection:
        for model in reversed(list(TABLES.values())):
            connection.execute(model.__table__.delete())
        for name, model in TABLES.items():
            path = data_dir / f"{name}.csv"
            records = _records(name, path)
            for start in range(0, len(records), 2000):
                connection.execute(insert(model), records[start : start + 2000])
            counts[name] = len(records)
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load processed and synthetic data into MySQL or SQLite.")
    parser.add_argument("--data-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--database-url")
    arguments = parser.parse_args()
    print(load_processed_data(arguments.data_dir, arguments.database_url))
