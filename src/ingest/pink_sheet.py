"""World Bank Pink Sheet: monthly commodity prices in USD (gold, crude oil).

The file URL changes with each release, so it is read from the Commodity Markets page.
"""

import csv
import re

import pandas as pd
import requests

from src.common import (
    LANDING,
    USER_AGENT,
    PipelineError,
    download,
    latest_download,
    raw_path,
)

PAGE = "https://www.worldbank.org/en/research/commodity-markets"
SOURCE = "worldbank"
SERIES = {
    "Gold": ("gold_usd_per_troy_oz", "($/troy oz)"),
    "Crude oil, average": ("crude_avg_usd_per_bbl", "($/bbl)"),
    "Crude oil, Brent": ("crude_brent_usd_per_bbl", "($/bbl)"),
    "Crude oil, WTI": ("crude_wti_usd_per_bbl", "($/bbl)"),
}


def download_all() -> None:
    page = requests.get(PAGE, headers={"User-Agent": USER_AGENT}, timeout=120)
    if page.status_code != 200:
        raise PipelineError(f"World Bank commodity page: HTTP {page.status_code}")
    links = set(re.findall(r'https?://[^"\']+CMO-Historical-Data-Monthly\.xlsx', page.text))
    if len(links) != 1:
        raise PipelineError(f"Expected one Pink Sheet monthly link, found {sorted(links)}")
    download(links.pop(), raw_path(SOURCE, "pink_sheet_monthly", "xlsx"))


def land() -> None:
    path = latest_download(SOURCE, "pink_sheet_monthly_dl*.xlsx")
    sheet = pd.read_excel(path, sheet_name="Monthly Prices", header=None)
    header_rows = sheet.index[sheet.apply(lambda r: "Gold" in r.values, axis=1)]
    if len(header_rows) != 1:
        raise PipelineError("Could not find the header row in the Pink Sheet")
    h = header_rows[0]
    names, units = sheet.iloc[h], sheet.iloc[h + 1]
    rows = []
    for col_name, (series, unit) in SERIES.items():
        cols = [c for c in sheet.columns if names[c] == col_name]
        if len(cols) != 1:
            raise PipelineError(f"Pink Sheet column not found once: {col_name}")
        col = cols[0]
        if units[col] != unit:
            raise PipelineError(f"Unit changed for {col_name}: {units[col]!r}, expected {unit}")
        for _, r in sheet.iloc[h + 2 :].iterrows():
            label, value = r[0], r[col]
            if not isinstance(label, str) or not re.fullmatch(r"\d{4}M\d{2}", label):
                continue
            if isinstance(value, str):  # "…" marks a missing value in the source
                continue
            rows.append((f"{label[:4]}-{label[5:]}-01", series, float(value)))
    with open(LANDING / "prices.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["month", "series", "value"])
        writer.writerows(rows)
