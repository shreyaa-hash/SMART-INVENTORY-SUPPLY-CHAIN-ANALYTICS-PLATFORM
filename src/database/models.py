from __future__ import annotations

from sqlalchemy import CheckConstraint, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Category(Base):
    __tablename__ = "categories"
    category_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    category_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    data_source: Mapped[str] = mapped_column(String(100), nullable=False)


class Supplier(Base):
    __tablename__ = "suppliers"
    supplier_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    supplier_name: Mapped[str] = mapped_column(String(150), nullable=False)
    data_source: Mapped[str] = mapped_column(String(100), nullable=False)


class Warehouse(Base):
    __tablename__ = "warehouses"
    warehouse_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    warehouse_name: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str] = mapped_column(String(50), nullable=False)
    data_source: Mapped[str] = mapped_column(String(100), nullable=False)


class Product(Base):
    __tablename__ = "products"
    product_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.category_id"), nullable=False, index=True)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.supplier_id"), nullable=False, index=True)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_unit_cost: Mapped[float] = mapped_column(Float, nullable=False)
    data_source: Mapped[str] = mapped_column(String(100), nullable=False)
    __table_args__ = (
        CheckConstraint("unit_price >= 0", name="ck_products_price_nonnegative"),
        CheckConstraint("estimated_unit_cost >= 0", name="ck_products_cost_nonnegative"),
    )


class Order(Base):
    __tablename__ = "orders"
    order_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    order_date: Mapped[DateTime] = mapped_column(DateTime, nullable=False, index=True)
    customer_country: Mapped[str] = mapped_column(String(100), nullable=False)
    warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.warehouse_id"), nullable=False, index=True)
    data_source: Mapped[str] = mapped_column(String(100), nullable=False)


class OrderItem(Base):
    __tablename__ = "order_items"
    order_item_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.order_id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.product_id"), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    line_revenue: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_cogs: Mapped[float] = mapped_column(Float, nullable=False)
    data_source: Mapped[str] = mapped_column(String(100), nullable=False)
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_order_items_price_nonnegative"),
    )


class Inventory(Base):
    __tablename__ = "inventory"
    product_id: Mapped[str] = mapped_column(ForeignKey("products.product_id"), primary_key=True)
    warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.warehouse_id"), primary_key=True)
    as_of_date: Mapped[Date] = mapped_column(Date, primary_key=True)
    quantity_on_hand: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_unit_cost: Mapped[float] = mapped_column(Float, nullable=False)
    data_source: Mapped[str] = mapped_column(String(120), nullable=False)
    __table_args__ = (
        CheckConstraint("quantity_on_hand >= 0", name="ck_inventory_nonnegative"),
        CheckConstraint("estimated_unit_cost >= 0", name="ck_inventory_cost_nonnegative"),
    )


class SupplierDelivery(Base):
    __tablename__ = "supplier_deliveries"
    delivery_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.supplier_id"), nullable=False, index=True)
    order_date: Mapped[Date] = mapped_column(Date, nullable=False)
    promised_date: Mapped[Date] = mapped_column(Date, nullable=False, index=True)
    actual_delivery_date: Mapped[Date] = mapped_column(Date, nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False)
    on_time: Mapped[int] = mapped_column(Integer, nullable=False)
    data_source: Mapped[str] = mapped_column(String(100), nullable=False)
    __table_args__ = (CheckConstraint("lead_time_days >= 0", name="ck_delivery_lead_nonnegative"),)


class DailySale(Base):
    __tablename__ = "daily_sales"
    product_id: Mapped[str] = mapped_column(ForeignKey("products.product_id"), primary_key=True)
    warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.warehouse_id"), primary_key=True)
    sales_date: Mapped[Date] = mapped_column(Date, primary_key=True, index=True)
    units_sold: Mapped[int] = mapped_column(Integer, nullable=False)
    revenue: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_cogs: Mapped[float] = mapped_column(Float, nullable=False)
    data_source: Mapped[str] = mapped_column(String(100), nullable=False)
    __table_args__ = (CheckConstraint("units_sold > 0", name="ck_daily_sales_units_positive"),)
