"""Bank of Canada Valet API: FXMUSDCAD, monthly average of the US dollar in Canadian dollars."""

import csv
import json

from src.common import LANDING, PipelineError, download, latest_download, raw_path

URL = "https://www.bankofcanada.ca/valet/observations/FXMUSDCAD/json?start_date=2015-01-01"
SOURCE = "bankofcanada"


def download_all() -> None:
    download(URL, raw_path(SOURCE, "fxmusdcad", "json"))


def land() -> None:
    data = json.loads(latest_download(SOURCE, "fxmusdcad_dl*.json").read_text())
    label = data["seriesDetail"]["FXMUSDCAD"]["label"]
    if label != "USD/CAD":
        raise PipelineError(f"Unexpected FXMUSDCAD label: {label}")
    rows = [(o["d"], float(o["FXMUSDCAD"]["v"])) for o in data["observations"]]
    if not rows:
        raise PipelineError("No FXMUSDCAD observations")
    with open(LANDING / "fx.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["month", "usdcad"])
        writer.writerows(rows)
