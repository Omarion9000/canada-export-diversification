"""StatCan Web Data Service (WDS): tables 12-10-0011, 12-10-0171, 12-10-0168, 12-10-0182.

Members are looked up by their English names in the cube metadata, so a renamed member
stops the pipeline instead of silently pulling the wrong series.
"""

import csv
import json

from src.common import (
    LANDING,
    PipelineError,
    download_date,
    latest_download,
    post_json,
    raw_path,
    register,
)

WDS = "https://www150.statcan.gc.ca/t1/wds/rest"
SOURCE = "statcan_wds"
BATCH = 50

# For each table: which members to pull, by dimension name -> list of member names.
# "*" means every member of that dimension.
TABLES = {
    "12100011": {
        "latest_n": 150,
        "select": {
            "Geography": ["Canada"],
            "Trade": ["Export"],
            "Basis": ["Customs", "Balance of payments"],
            "Seasonal adjustment": ["Unadjusted"],
            "Principal trading partners": "*",
        },
    },
    "12100182": {
        "latest_n": 150,
        "select": {
            "Geography": ["Canada"],
            "North American Product Classification System (NAPCS)": [
                "All sections",
                "Unwrought gold, silver, and platinum group metals, and their alloys",
            ],
            "Trade": ["Domestic exports"],
            "Principal trading partner: Exports by country of destination": "*",
            "Principal trading partner: Exports by country of origin": [
                "All countries, country of origin"
            ],
        },
    },
    "12100171": {
        "latest_n": 15,
        "select": {
            "Geography": ["Canada"],
            "Trading partner": "*",
            "North American Product Classification System (NAPCS)": ["All sections"],
            "Trade": ["Export"],
        },
    },
    "12100168": {
        "latest_n": 150,
        "select": {
            "Geography": ["Canada"],
            "Trade": ["Export"],
            "Basis": ["Customs", "Balance of payments"],
            "Seasonal adjustment": ["Unadjusted"],
            "Index": ["Price index", "Volume index"],
            "Weighting": ["Laspeyres fixed weighted"],
            "North American Product Classification System (NAPCS)": [
                "Total of all merchandise",
                "Crude oil and crude bitumen",
                "Unwrought gold, silver, and platinum group metals, and their alloys",
            ],
        },
    },
}


def metadata(pid: str) -> dict:
    result = post_json(f"{WDS}/getCubeMetadata", [{"productId": int(pid)}])
    if result[0].get("status") != "SUCCESS":
        raise PipelineError(f"WDS metadata failed for {pid}: {result[0]}")
    return result[0]["object"]


def coordinates(meta: dict, select: dict) -> list[tuple[str, list[str]]]:
    """Build 10-part WDS coordinates for every combination of selected members."""
    dims = meta["dimension"]
    names = [d["dimensionNameEn"] for d in dims]
    if set(select) != set(names):
        raise PipelineError(f"Dimension names changed for {meta['productId']}: {names}")
    options = []
    for d in dims:
        wanted = select[d["dimensionNameEn"]]
        members = d["member"]
        if wanted == "*":
            chosen = members
        else:
            by_name = {m["memberNameEn"]: m for m in members}
            missing = [w for w in wanted if w not in by_name]
            if missing:
                raise PipelineError(f"Members not found in {meta['productId']}: {missing}")
            chosen = [by_name[w] for w in wanted]
        options.append([(str(m["memberId"]), m["memberNameEn"]) for m in chosen])
    combos = [([], [])]
    for opts in options:
        combos = [(ids + [i], labels + [n]) for ids, labels in combos for i, n in opts]
    return [(".".join(ids + ["0"] * (10 - len(ids))), labels) for ids, labels in combos]


def normalize(coordinate: str) -> str:
    """WDS coordinates always have 10 parts."""
    parts = coordinate.split(".")
    return ".".join(parts + ["0"] * (10 - len(parts)))


def download_all() -> None:
    for pid, spec in TABLES.items():
        dest = raw_path(SOURCE, f"table_{pid}", "json")
        register(dest, f"{WDS}/getDataFromCubePidCoordAndLatestNPeriods (productId {pid})")
        if dest.exists():
            continue
        meta = metadata(pid)
        coords = coordinates(meta, spec["select"])
        series = []
        for i in range(0, len(coords), BATCH):
            chunk = coords[i : i + BATCH]
            payload = [
                {"productId": int(pid), "coordinate": c, "latestN": spec["latest_n"]}
                for c, _ in chunk
            ]
            for (coord, labels), item in zip(chunk, post_json(
                f"{WDS}/getDataFromCubePidCoordAndLatestNPeriods", payload
            ), strict=True):
                series.append({"coordinate": coord, "labels": labels, "response": item})
        dest.parent.mkdir(parents=True, exist_ok=True)
        dims = [d["dimensionNameEn"] for d in meta["dimension"]]
        dest.write_text(json.dumps({"productId": pid, "dimensions": dims, "series": series}))


def land() -> None:
    """Write one tidy CSV per table: dimension labels, ref_date, value in dollars (or index)."""
    for pid in TABLES:
        path = latest_download(SOURCE, f"table_{pid}_dl*.json")
        data = json.loads(path.read_text())
        dims = [d.lower().replace(" ", "_").replace(":", "").replace("(", "").replace(")", "")
                for d in data["dimensions"]]
        # WDS does not return series in request order: match each answer by its coordinate.
        labels_by_coord = {s["coordinate"]: s["labels"] for s in data["series"]}
        rows, no_data, seen = [], [], set()
        for s in data["series"]:
            response = s["response"]
            if response.get("status") != "SUCCESS":
                # WDS answers FAILED for a coordinate that has no series (no trade recorded).
                no_data.append(s["coordinate"])
                continue
            obj = response["object"]
            coord = normalize(obj["coordinate"])
            if coord not in labels_by_coord or coord in seen:
                raise PipelineError(f"Table {pid}: unexpected or repeated coordinate {coord}")
            seen.add(coord)
            labels = labels_by_coord[coord]
            for point in obj["vectorDataPoint"]:
                if point["value"] is None:
                    continue
                scale = 10 ** int(point["scalarFactorCode"])
                rows.append(labels + [point["refPer"], point["value"] * scale,
                                           point["statusCode"], point["symbolCode"]])
        if not rows:
            raise PipelineError(f"No data points landed for table {pid}")
        out = LANDING / f"statcan_{pid}.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(dims + ["ref_date", "value", "status_code", "symbol_code"])
            writer.writerows(rows)
        note = LANDING / f"statcan_{pid}_no_series.txt"
        note.write_text("\n".join(no_data))
        print(f"  {pid}: {len(rows)} points, {len(no_data)} coordinates without a series, "
              f"vintage {download_date(path)}")
