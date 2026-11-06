"""Shared paths, settings and download helpers.

Every raw download is saved once under data/raw/<source>/ with the download date in the
file name. Raw files are never edited. Parsed, tidy versions go to data/processed/landing/.
"""

import datetime as dt
import re
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
LANDING = PROCESSED / "landing"
CSV_OUT = PROCESSED / "csv"
SQL_DIR = ROOT / "sql"
DOCS = ROOT / "docs"
DB_PATH = PROCESSED / "trade.duckdb"

USER_AGENT = "canada-export-diversification/0.1 (public research pipeline)"
TIMEOUT_SECONDS = 300


class PipelineError(RuntimeError):
    """Raised when a pipeline step cannot continue. Never caught silently."""


def load_settings() -> dict:
    with open(CONFIG / "settings.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def today() -> str:
    return dt.date.today().isoformat()


def raw_path(source: str, name: str, ext: str, date: str | None = None) -> Path:
    """Path of a raw file: data/raw/<source>/<name>_dl<date>.<ext>."""
    return RAW / source / f"{name}_dl{date or today()}.{ext}"


# Source URL of every raw file touched in this run (written to data/raw/MANIFEST.csv).
SOURCE_URLS: dict[Path, str] = {}


def register(path: Path, url: str) -> None:
    SOURCE_URLS[path] = url


def download(url: str, dest: Path, allow_404: bool = False) -> Path | None:
    """Download url to dest once. Existing files are kept as they are (raw is immutable).

    Returns None only when allow_404 is True and the server answers 404.
    """
    register(dest, url)
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_SECONDS)
    if response.status_code == 404 and allow_404:
        SOURCE_URLS.pop(dest)
        return None
    if response.status_code != 200:
        raise PipelineError(f"Download failed: HTTP {response.status_code} for {url}")
    if not response.content:
        raise PipelineError(f"Download returned an empty body: {url}")
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.write_bytes(response.content)
    tmp.rename(dest)
    return dest


def post_json(url: str, payload) -> object:
    response = requests.post(
        url, json=payload, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_SECONDS
    )
    if response.status_code != 200:
        raise PipelineError(f"POST failed: HTTP {response.status_code} for {url}")
    return response.json()


def latest_download(source: str, pattern: str) -> Path:
    """Newest raw file in data/raw/<source>/ whose name matches pattern (a glob)."""
    files = sorted((RAW / source).glob(pattern), key=download_date)
    if not files:
        raise PipelineError(f"No raw files for {source}/{pattern}. Run `make ingest` first.")
    return files[-1]


def download_date(path: Path) -> str:
    match = re.search(r"_dl(\d{4}-\d{2}-\d{2})", path.name)
    if not match:
        raise PipelineError(f"Raw file name has no download date: {path.name}")
    return match.group(1)
