import json

import pandas as pd

from src.data_processing.pipeline import process_dataset


def test_pipeline_cleans_transactions_and_labels_synthetic_data(tmp_path):
    source = tmp_path / "source.xlsx"
    rows = [
        ["10001", "A1", "CUP", 2, "2010-01-01", 5.0, 100.0, "UK"],
        ["10001", "A1", "CUP", 2, "2010-01-01", 5.0, 100.0, "UK"],
        ["10002", "B2", None, 1, "2010-01-02", 4.0, None, "UK"],
        ["C10003", "A1", "CUP", -1, "2010-01-03", 5.0, 100.0, "UK"],
    ]
    columns = ["Invoice", "StockCode", "Description", "Quantity", "InvoiceDate", "Price", "Customer ID", "Country"]
    with pd.ExcelWriter(source) as writer:
        pd.DataFrame(rows, columns=columns).to_excel(writer, sheet_name="Year 2009-2010", index=False)
    report = process_dataset(source, tmp_path / "data" / "processed")
    cleaned = pd.read_csv(tmp_path / "data" / "processed" / "cleaned_transactions.csv")
    inventory = pd.read_csv(tmp_path / "data" / "processed" / "inventory.csv")
    assert report["total_source_records"] == 4
    assert report["duplicate_count_removed"] == 1
    assert len(cleaned) == 2
    assert cleaned["quantity"].gt(0).all()
    assert inventory["data_source"].str.contains("synthetic").all()
    assert json.loads((tmp_path / "reports" / "data_quality.json").read_text())["invalid_records_excluded"] >= 1
