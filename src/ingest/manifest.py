"""Writes data/raw/MANIFEST.csv: one row per raw file with its source URL and checksum."""

import csv
import hashlib

from src.common import RAW, SOURCE_URLS, PipelineError, download_date

MANIFEST = RAW / "MANIFEST.csv"
FIELDS = ["file", "source_url", "download_date", "sha256", "size_bytes"]


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write() -> None:
    known = {}
    if MANIFEST.exists():
        with open(MANIFEST, encoding="utf-8") as f:
            known = {r["file"]: r["source_url"] for r in csv.DictReader(f)}
    for path, url in SOURCE_URLS.items():
        known[str(path.relative_to(RAW))] = url
    files = sorted(p for p in RAW.rglob("*") if p.is_file() and p.name not in
                   (MANIFEST.name, ".gitkeep") and not p.name.endswith(".part"))
    rows = []
    for path in files:
        rel = str(path.relative_to(RAW))
        if rel not in known:
            raise PipelineError(f"No source URL recorded for raw file {rel}")
        rows.append({"file": rel, "source_url": known[rel],
                     "download_date": download_date(path),
                     "sha256": sha256(path), "size_bytes": path.stat().st_size})
    with open(MANIFEST, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  {MANIFEST.relative_to(RAW.parent.parent)}: {len(rows)} files")
