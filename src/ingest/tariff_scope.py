"""Official US tariff product lists, parsed to HTS codes, plus the US HTS line universe.

Lists come from CBP CSMS attachments and proclamation annexes (config/tariff_lists.csv).
The USITC HTS export gives every 8-digit US tariff line, so staging can tell whether a
list covers all lines of an HS6 code (full) or only some (partial).
"""

import csv
import html
import json
import re
import zipfile
from pathlib import Path

from pypdf import PdfReader

from src.common import (
    CONFIG,
    LANDING,
    PipelineError,
    download,
    latest_download,
    raw_path,
)

SOURCE = "tariff_lists"
USITC_URL = "https://hts.usitc.gov/reststop/exportList?from=0101&to=9999&format=JSON&styles=false"
USITC_RELEASE_URL = "https://hts.usitc.gov/reststop/releaseList"
# 4-digit heading, 2-digit subheading, then optional 2 + 2 digits (HTS8, HTS10).
CODE = re.compile(r"(?<![\d.])(\d{4})\.(\d{2})(?:\.(\d{2})(?:\.(\d{2}))?)?(?![\d])")


def read_lists() -> list[dict]:
    with open(CONFIG / "tariff_lists.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def download_all() -> None:
    for item in read_lists():
        download(item["url"], raw_path(SOURCE, item["list_id"].lower(), item["format"]))
    download(USITC_URL, raw_path("usitc", "hts_export", "json"))
    download(USITC_RELEASE_URL, raw_path("usitc", "hts_releases", "json"))


def text_of(path: Path, fmt: str) -> str:
    if fmt == "pdf":
        return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    if fmt == "docx":
        xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
        return html.unescape(re.sub(r"<[^>]+>", " ", xml))
    if fmt == "html":
        raw = path.read_text(encoding="utf-8", errors="replace")
        raw = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw, flags=re.S)
        return html.unescape(re.sub(r"<[^>]+>", " ", raw))
    raise PipelineError(f"Unknown list format: {fmt}")


def parse_codes(text: str) -> set[tuple[str, int]]:
    """Return (code, level) pairs: digits only, level 6, 8 or 10. Chapters 98 and 99 dropped."""
    found = set()
    for m in CODE.finditer(text):
        heading, sub, hts8, hts10 = m.groups()
        if heading[:2] in ("98", "99"):
            continue
        code = heading + sub + (hts8 or "") + (hts10 or "")
        found.add((code, len(code)))
    return found


def land() -> None:
    rows = []
    for item in read_lists():
        path = latest_download(SOURCE, f"{item['list_id'].lower()}_dl*.{item['format']}")
        codes = parse_codes(text_of(path, item["format"]))
        if len(codes) < 5:
            raise PipelineError(f"{item['list_id']}: only {len(codes)} codes parsed; check file")
        rows += [(item["list_id"], code, level) for code, level in sorted(codes)]
        print(f"  {item['list_id']}: {len(codes)} codes")
    with open(LANDING / "tariff_list_codes.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["list_id", "code", "level"])
        writer.writerows(rows)

    export = json.loads(latest_download("usitc", "hts_export_dl*.json").read_text())
    # Many 8-digit lines appear only through their 10-digit statistical suffixes,
    # so take the 8-digit prefix of every code with at least 8 digits.
    lines = sorted({x["htsno"][:10].replace(".", "") for x in export
                    if x.get("htsno") and re.match(r"\d{4}\.\d{2}\.\d{2}", x["htsno"])
                    and x["htsno"][:2] not in ("98", "99")})
    if len(lines) < 10000:
        raise PipelineError(f"USITC export looks incomplete: {len(lines)} HTS8 lines")
    releases = json.loads(latest_download("usitc", "hts_releases_dl*.json").read_text())
    current = [r["name"] for r in releases if r.get("status") == "current"]
    with open(LANDING / "us_hts8.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["hts8", "hs6", "hts_release"])
        writer.writerows((code, code[:6], current[0] if current else "") for code in lines)
