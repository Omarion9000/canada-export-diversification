"""StatCan CIMT bulk files: domestic and total exports, HS6 x country x month.

Source: Canadian International Merchandise Trade Web Application (71-607-X), bulk CSV files
listed on the Open Government Portal. One ZIP per year and trade type.
"""

import csv
import datetime as dt
import shutil
import zipfile
from pathlib import Path

from src.common import LANDING, RAW, PipelineError, download, download_date, raw_path

BASE_URL = "https://www150.statcan.gc.ca/n1/pub/71-607-x/2021004/zip/CIMT-CICM_{kind}_{year}.zip"
SOURCE = "cimt"
# kind -> (file prefix inside the ZIP, landing name)
FILES = {
    "Dom_Exp": ("ODPFN018_", "dom_hs6"),  # domestic exports, HS6 detail
    "Tot_Exp": ("ODPFN021_", "tot_hs2"),  # total exports, HS2 detail (only used for V1a)
}
DESCRIPTION_FILES = {
    "ODPF_4_HS6XDesc.TXT": "hs6_desc",
    "ODPF_5_HS2Desc.TXT": "hs2_desc",
    "ODPF_6_CtyDesc.TXT": "country_desc",
}


def years(first_month: str) -> list[int]:
    return list(range(int(first_month[:4]), dt.date.today().year + 1))


def download_all(first_month: str) -> None:
    current_year = dt.date.today().year
    for kind in FILES:
        for year in years(first_month):
            url = BASE_URL.format(kind=kind, year=year)
            dest = raw_path(SOURCE, f"{kind.lower()}_{year}", "zip")
            # The file for a new year only appears after its first release.
            got = download(url, dest, allow_404=(year == current_year))
            if got is None:
                print(f"  {kind} {year}: not published yet (404), skipped")


def zips_for_date(kind: str, date: str) -> list[Path]:
    found = sorted((RAW / SOURCE).glob(f"{kind.lower()}_*_dl{date}.zip"))
    if not found:
        raise PipelineError(f"No CIMT {kind} files for download date {date}")
    return found


def latest_date() -> str:
    dates = {download_date(p) for p in (RAW / SOURCE).glob("dom_exp_*_dl*.zip")}
    if not dates:
        raise PipelineError("No CIMT downloads found. Run `make ingest`.")
    return max(dates)


def previous_date(current: str) -> str | None:
    dates = sorted({download_date(p) for p in (RAW / SOURCE).glob("dom_exp_*_dl*.zip")})
    older = [d for d in dates if d < current]
    return older[-1] if older else None


def extract(date: str, target: Path) -> None:
    """Unzip the CSVs used by the pipeline and the latest description files into target."""
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    for kind, (prefix, landing_name) in FILES.items():
        for zip_path in zips_for_date(kind, date):
            year = zip_path.name.split("_")[2]
            with zipfile.ZipFile(zip_path) as z:
                members = [m for m in z.namelist() if Path(m).name.startswith(prefix)]
                if len(members) != 1:
                    raise PipelineError(f"Expected one {prefix}* file in {zip_path.name}")
                out = target / f"{landing_name}_{year}.csv"
                with z.open(members[0]) as src, open(out, "wb") as dst:
                    shutil.copyfileobj(src, dst)
    # Description files: take them from the newest domestic-exports ZIP.
    newest = zips_for_date("Dom_Exp", date)[-1]
    with zipfile.ZipFile(newest) as z:
        for name, landing_name in DESCRIPTION_FILES.items():
            members = [m for m in z.namelist() if Path(m).name == name]
            if len(members) != 1:
                raise PipelineError(f"Expected {name} in {newest.name}")
            text = z.read(members[0]).decode("latin-1")
            write_description(text, landing_name, target)


def write_description(text: str, kind: str, target: Path) -> None:
    """Convert a fixed-width StatCan description file to CSV.

    Layout: code [0:11], start YYYYMM [11:17], end YYYYMM [18:24], then for HS6 files a
    3-letter unit at [25:28] and the English text at [29:112]; for HS2 and country files the
    English text at [25:108].
    """


    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        code, start, end = line[0:11].split()[0], line[11:17], line[18:24]
        if not (start.isdigit() and end.isdigit()):
            raise PipelineError(f"Unexpected layout in {kind}: {line[:40]!r}")
        if kind == "hs6_desc":
            unit, text_en = line[25:28].strip(), line[29:112].strip()
            if line[111] != " ":
                raise PipelineError(f"HS6 description overflows its column: {line[:40]!r}")
            rows.append((code, start, end, unit, text_en))
        else:
            if line[107] != " ":
                raise PipelineError(f"{kind} text overflows its column: {line[:40]!r}")
            rows.append((code, start, end, line[25:108].strip()))
    header = ["code", "start_yyyymm", "end_yyyymm"] + (
        ["unit", "description"] if kind == "hs6_desc" else ["name"]
    )
    with open(target / f"{kind}.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def land() -> str:
    """Extract the latest download (and the previous one, for V6). Returns the vintage date."""
    current = latest_date()
    extract(current, LANDING / "cimt")
    previous = previous_date(current)
    prev_dir = LANDING / "cimt_previous"
    if prev_dir.exists():
        shutil.rmtree(prev_dir)
    if previous:
        extract(previous, prev_dir)
        (prev_dir / "VINTAGE").write_text(previous)
    (LANDING / "cimt" / "VINTAGE").write_text(current)
    return current
