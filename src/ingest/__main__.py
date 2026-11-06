"""`python -m src.ingest`: download every source (once per day), then write landing files."""

from src.common import LANDING, load_settings
from src.ingest import boc_valet, cimt, manifest, pink_sheet, sccai, statcan_wds, tariff_scope


def main() -> None:
    settings = load_settings()
    LANDING.mkdir(parents=True, exist_ok=True)
    steps = [
        ("StatCan CIMT", lambda: cimt.download_all(settings["data"]["first_month"]), cimt.land),
        ("StatCan WDS tables", statcan_wds.download_all, statcan_wds.land),
        ("World Bank Pink Sheet", pink_sheet.download_all, pink_sheet.land),
        ("Bank of Canada FX", boc_valet.download_all, boc_valet.land),
        ("StatCan SCCAI country codes", sccai.download_all, sccai.land),
        ("US tariff lists and HTS", tariff_scope.download_all, tariff_scope.land),
    ]
    for name, fetch, land in steps:
        print(f"[ingest] {name}")
        fetch()
        land()
    print("[ingest] Raw file manifest")
    manifest.write()


if __name__ == "__main__":
    main()
