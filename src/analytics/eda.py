from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

sns.set_theme(style="whitegrid", palette="deep")


def run_eda(data_dir: Path = Path("data/processed"), report_dir: Path = Path("reports")) -> list[str]:
    figures = report_dir / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    daily = pd.read_csv(data_dir / "daily_sales.csv", parse_dates=["sales_date"], dtype={"product_id": str}, low_memory=False)
    products = pd.read_csv(data_dir / "products.csv", dtype={"product_id": str}, low_memory=False)
    categories = pd.read_csv(data_dir / "categories.csv")
    inventory = pd.read_csv(data_dir / "inventory.csv")
    suppliers = pd.read_csv(data_dir / "supplier_deliveries.csv")
    sales = pd.read_csv(data_dir / "cleaned_transactions.csv", parse_dates=["invoice_date"], dtype={"invoice_id": str, "product_id": str}, low_memory=False)

    observations: list[str] = [
        f"The cleaned dataset contains {len(sales):,} positive, non-cancelled observed order lines "
        f"from {sales.invoice_date.min().date()} through {sales.invoice_date.max().date()}.",
        f"Observed line revenue totals GBP {sales.line_revenue.sum():,.2f}; all amounts use the source's "
        "recorded unit prices and quantities.",
    ]

    monthly = sales.assign(month=sales.invoice_date.dt.to_period("M").astype(str)).groupby("month").line_revenue.sum()
    fig, ax = plt.subplots(figsize=(12, 5))
    monthly.plot(ax=ax, color="#2563eb", linewidth=2)
    ax.set(title="Observed revenue by month", xlabel="Invoice month", ylabel="Revenue (GBP)")
    ax.tick_params(axis="x", rotation=55)
    fig.tight_layout()
    fig.savefig(figures / "monthly_revenue.png", dpi=150)
    plt.close(fig)
    peak_month = monthly.idxmax()
    observations.append(
        f"Monthly observed revenue peaks in {peak_month} at GBP {monthly.max():,.2f}; this is historical "
        "descriptive evidence, not a forward projection."
    )

    top = sales.groupby(["product_id", "description"], as_index=False).agg(
        revenue=("line_revenue", "sum"), units=("quantity", "sum")
    ).nlargest(12, "revenue").sort_values("revenue")
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(top.product_id.astype(str) + " · " + top.description.str.slice(0, 34), top.revenue, color="#0f766e")
    ax.set(title="Which products contribute the most observed revenue?", xlabel="Revenue (GBP)", ylabel="Product")
    fig.tight_layout()
    fig.savefig(figures / "top_products_revenue.png", dpi=150)
    plt.close(fig)
    observations.append(
        f"The top 10 products contribute GBP {top.nlargest(10, 'revenue').revenue.sum():,.2f} in observed "
        "line revenue. Product ranking is based on actual UCI transaction lines."
    )

    category_lookup = products.set_index("product_id")["category_id"]
    category_lookup_names = categories.set_index("category_id")["category_name"]
    category_sales = (
        sales.assign(category_id=sales.product_id.map(category_lookup))
        .groupby("category_id")
        .line_revenue.sum()
        .rename(index=category_lookup_names)
        .sort_values()
    )
    fig, ax = plt.subplots(figsize=(9, 5))
    category_sales.plot.barh(ax=ax, color="#7c3aed")
    ax.set(title="Observed revenue by inferred product category", xlabel="Revenue (GBP)", ylabel="Inferred category")
    fig.tight_layout()
    fig.savefig(figures / "category_revenue.png", dpi=150)
    plt.close(fig)
    observations.append(
        "Category labels are inferred from product descriptions for demonstration only; their revenue aggregates "
        "are observed transactions grouped by those synthetic labels."
    )

    coverage = inventory.groupby("product_id").agg(stock=("quantity_on_hand", "sum"))
    demand = daily.groupby("product_id").units_sold.sum()
    coverage["lifetime_units"] = demand
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.scatterplot(data=coverage, x="lifetime_units", y="stock", alpha=0.55, s=22, ax=ax)
    ax.set(title="Synthetic on-hand stock versus observed lifetime units", xlabel="Observed units sold", ylabel="Synthetic units on hand")
    fig.tight_layout()
    fig.savefig(figures / "stock_vs_sales.png", dpi=150)
    plt.close(fig)
    observations.append(
        f"The synthetic inventory snapshot has {int((coverage.stock == 0).sum()):,} products with zero demo "
        f"stock and {int((coverage.stock > 0).sum()):,} with positive demo stock; it is not measured company stock."
    )

    reliability = suppliers.groupby("supplier_id").agg(
        lead_time_days=("lead_time_days", "mean"), on_time_pct=("on_time", lambda x: x.mean() * 100)
    ).sort_values("on_time_pct")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(reliability.index, reliability.on_time_pct, color="#d97706")
    ax.set(title="Demonstration supplier on-time rate (synthetic)", xlabel="Synthetic supplier", ylabel="On-time deliveries (%)", ylim=(0, 100))
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(figures / "supplier_reliability.png", dpi=150)
    plt.close(fig)
    observations.append(
        f"Synthetic supplier on-time delivery rates range from {reliability.on_time_pct.min():.1f}% to "
        f"{reliability.on_time_pct.max():.1f}%; these are reproducible scenarios, not measured supplier performance."
    )

    sales["month_num"] = sales.invoice_date.dt.month
    seasonal = sales.groupby("month_num").line_revenue.mean()
    fig, ax = plt.subplots(figsize=(9, 5))
    seasonal.plot(marker="o", ax=ax, color="#be123c")
    ax.set(title="Average order-line revenue by calendar month", xlabel="Calendar month", ylabel="Mean line revenue (GBP)")
    fig.tight_layout()
    fig.savefig(figures / "monthly_seasonality.png", dpi=150)
    plt.close(fig)
    observations.append(
        f"Average line revenue is highest in calendar month {int(seasonal.idxmax())}; the two-year history is "
        "short, so seasonality should be treated as exploratory."
    )

    numeric = sales[["quantity", "unit_price", "line_revenue"]].corr()
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(numeric, annot=True, fmt=".2f", cmap="vlag", center=0, ax=ax)
    ax.set(title="How do observed quantity, price, and revenue move together?")
    fig.tight_layout()
    fig.savefig(figures / "sales_correlation.png", dpi=150)
    plt.close(fig)
    observations.append(
        f"The quantity/revenue correlation is {numeric.loc['quantity', 'line_revenue']:.2f} and price/revenue "
        f"correlation is {numeric.loc['unit_price', 'line_revenue']:.2f}; correlations are descriptive, not causal."
    )

    report_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Business insights from observed retail transactions",
        "",
        "## Scope and provenance",
        "Observed measures come from the UCI Online Retail II public workbook (GBP prices, invoice lines, 2009–2011). "
        "Cancelled invoices, non-positive quantities/prices, invalid keys/dates, and exact duplicates were excluded. "
        "Inventory, unit costs, categories, suppliers, delivery events, and warehouse assignments are synthetic "
        "demonstrations and must not be interpreted as company history.",
        "",
        "## Findings",
        *[f"- {text}" for text in observations],
        "",
        "## Visual evidence",
        *[f"- [{path.stem}](./figures/{path.name})" for path in sorted(figures.glob("*.png"))],
        "",
        "## Decisions to validate with real operational data",
        "- Replace the synthetic stock snapshot, purchase costs, warehouse mapping, and supplier events before using reorder or margin recommendations operationally.",
        "- Use actual purchasing and stockout-event history to calibrate safety stock and holding-cost assumptions.",
        "- Use a chronological holdout and compare forecast errors by product before automating replenishment.",
        "",
    ]
    (report_dir / "business_insights.md").write_text("\n".join(lines), encoding="utf-8")
    return observations


if __name__ == "__main__":
    for finding in run_eda():
        print(f"- {finding}")
