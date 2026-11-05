from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.main import create_app
from src.database.connection import get_engine
from src.database.models import (
    Base, Category, DailySale, Inventory, Order, OrderItem, Product,
    Supplier, SupplierDelivery, Warehouse,
)


def _seed(engine):
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(
            [
                Category(category_id="CAT-01", category_name="General", data_source="synthetic"),
                Supplier(supplier_id="SUP-001", supplier_name="Demo supplier", data_source="synthetic"),
                Warehouse(warehouse_id="WH-01", warehouse_name="Demo hub", region="Demo", data_source="synthetic"),
            ]
        )
        session.flush()
        session.add(
            Product(
                product_id="P1", description="Demo item", category_id="CAT-01", supplier_id="SUP-001",
                unit_price=10, estimated_unit_cost=6, data_source="observed + synthetic",
            )
        )
        session.add(Order(order_id="ORD-1", order_date=datetime(2020, 1, 1), customer_country="UK", warehouse_id="WH-01", data_source="observed"))
        session.flush()
        session.add(OrderItem(order_item_id=1, order_id="ORD-1", product_id="P1", quantity=2, unit_price=10, line_revenue=20, estimated_cogs=12, data_source="observed"))
        session.add(Inventory(product_id="P1", warehouse_id="WH-01", as_of_date=date(2020, 5, 1), quantity_on_hand=20, estimated_unit_cost=6, data_source="synthetic"))
        start = date(2020, 1, 1)
        session.add_all(
            [
                DailySale(product_id="P1", warehouse_id="WH-01", sales_date=start + timedelta(days=day), units_sold=2, revenue=20, estimated_cogs=12, data_source="observed")
                for day in range(120)
            ]
        )
        session.add(SupplierDelivery(delivery_id="DEL-1", supplier_id="SUP-001", order_date=start, promised_date=start + timedelta(days=5), actual_delivery_date=start + timedelta(days=5), lead_time_days=5, on_time=1, data_source="synthetic"))
        session.commit()


def test_api_serves_database_metrics_products_and_forecast(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'api.db'}"
    engine = get_engine(database_url)
    _seed(engine)
    with TestClient(create_app(database_url)) as client:
        assert client.get("/api/health").json()["status"] == "ok"
        overview = client.get("/api/dashboard/overview").json()
        assert overview["revenue"] == 20
        assert overview["products"] == 1
        assert client.get("/api/products").json()["total"] == 1
        assert client.get("/api/sales/monthly").json()[0]["month"] == "2020-01"
        assert client.get("/api/sales/categories").json()[0]["revenue"] == 20
        assert client.get("/api/sales/regions").json()[0]["country"] == "UK"
        assert client.get("/api/sales/history/P1").json()
        assert client.get("/api/inventory/summary").json()["available_stock"] == 20
        assert client.get("/api/inventory/products").json()[0]["product_id"] == "P1"
        assert client.get("/api/inventory/low-stock").status_code == 200
        assert client.get("/api/inventory/overstock").status_code == 200
        assert client.get("/api/suppliers/performance").json()[0]["deliveries"] == 1
        assert client.get("/api/warehouses").json()[0]["stock"] == 20
        assert client.get("/api/recommendations").status_code == 200
        forecast = client.get("/api/forecast/P1?horizon_days=7").json()
        assert forecast["warning"] is None
        assert len(forecast["forecasts"]) == 7


def test_sqlite_enforces_foreign_keys(tmp_path):
    engine = get_engine(f"sqlite:///{tmp_path / 'fk.db'}")
    Base.metadata.create_all(engine)
    with pytest.raises(IntegrityError):
        with Session(engine) as session:
            session.add(Order(order_id="bad", order_date=datetime(2020, 1, 1), customer_country="UK", warehouse_id="missing", data_source="observed"))
            session.commit()
