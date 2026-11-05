from __future__ import annotations

import os
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

from src.data_processing.pipeline import extract_dataset

load_dotenv()


def main() -> None:
    raw_dir = Path("data/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    archive = raw_dir / "online_retail_ii.zip"
    url = os.getenv(
        "DATASET_DOWNLOAD_URL",
        "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip",
    )
    if not archive.exists():
        print(f"Downloading public UCI dataset: {url}")
        request = urllib.request.Request(url, headers={"User-Agent": "smart-inventory-analytics/1.0"})
        with urllib.request.urlopen(request, timeout=60) as response, archive.open("wb") as target:
            target.write(response.read())
    workbook = extract_dataset(archive, raw_dir)
    print(f"Source workbook ready at {workbook}")


if __name__ == "__main__":
    main()
