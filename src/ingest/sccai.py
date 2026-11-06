"""StatCan Standard Classification of Countries and Areas of Interest (SCCAI) 2019.

Gives ISO alpha-2 and alpha-3 codes for every country StatCan uses, including Taiwan.
"""

import csv

from src.common import LANDING, PipelineError, download, latest_download, raw_path

URL = "https://www.statcan.gc.ca/en/statistical-programs/document/sccai-2019-structure.csv"
SOURCE = "statcan_sccai"


def download_all() -> None:
    download(URL, raw_path(SOURCE, "sccai_2019_structure", "csv"))


def land() -> None:
    path = latest_download(SOURCE, "sccai_2019_structure_dl*.csv")
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    expected = {"Code", "Countries and Areas of Interest", "Num-3", "Alpha-2", "Alpha-3"}
    if not rows or not expected <= set(rows[0]):
        raise PipelineError(f"SCCAI columns changed: {list(rows[0]) if rows else 'empty'}")
    # The file repeats some rows (one per footnote); keep one row per alpha-2 code.
    pairs = {}
    for r in rows:
        iso2, iso3 = r["Alpha-2"].strip(), r["Alpha-3"].strip()
        if not iso2:
            continue
        if iso2 in pairs and pairs[iso2][0] != iso3:
            raise PipelineError(f"SCCAI gives two alpha-3 codes for {iso2}")
        pairs[iso2] = (iso3, r["Countries and Areas of Interest"].strip())
    if len(pairs) < 240:
        raise PipelineError(f"SCCAI looks incomplete: {len(pairs)} codes")
    with open(LANDING / "sccai.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["iso2", "iso3", "name"])
        writer.writerows((k, v[0], v[1]) for k, v in sorted(pairs.items()))
