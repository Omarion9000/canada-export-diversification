"""Builds excel/analyst_pack.xlsx: Summary, Sector exposure, Data and Sources sheets.

Every value comes from the marts (through src.analysis) or from docs/sources.md. Run after the
marts (`make excel`).
"""

import re

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

from src import analysis
from src.common import DOCS, ROOT, PipelineError, load_settings
from src.report import SECTOR_NAMES

OUT = ROOT / "excel" / "analyst_pack.xlsx"
BOLD = Font(bold=True)
TITLE = Font(bold=True, size=14)
MUTED = Font(color="52514E", italic=True)
HEADER_FILL = PatternFill("solid", fgColor="E1E0D9")
WRAP = Alignment(wrap_text=True, vertical="top")

VARIANTS = {
    "total": "All goods",
    "ex_gold": "Without gold",
    "ex_gold_ex_energy": "Without gold and energy",
}


def header(ws, row: int, names: list[str]) -> None:
    for col, name in enumerate(names, start=1):
        cell = ws.cell(row=row, column=col, value=name)
        cell.font = BOLD
        cell.fill = HEADER_FILL
        cell.alignment = WRAP


def widths(ws, values: dict[str, float]) -> None:
    for col, width in values.items():
        ws.column_dimensions[col].width = width


def summary_sheet(wb, con) -> None:
    ws = wb.active
    ws.title = "Summary"
    t = load_settings()["thresholds"]
    start, end = analysis.tariff_window(con)
    vintage = con.execute("select p('cimt_vintage')").fetchall()[0][0]
    ws["A1"] = "Canada export diversification under US tariffs: analyst pack"
    ws["A1"].font = TITLE
    ws["A2"] = (
        f"Statistics Canada, CIMT domestic exports (customs basis), data downloaded {vintage}. "
        f"Latest 12 months: {start}–{end}. Every value on these sheets is read from the project "
        f"marts; thresholds were frozen before the analysis."
    )
    ws["A2"].font = MUTED

    cols = [
        "Hypothesis",
        "Rule (frozen)",
        "Baseline",
        "Case",
        "Measure",
        "Value",
        "Threshold",
        "Verdict",
    ]
    header(ws, 4, cols)
    rows = []
    for baseline, label in analysis.BASELINES.items():
        for variant in ["total", "ex_gold_ex_energy"]:
            r = analysis.h1(con, baseline, variant)
            rows.append(
                [
                    "H1: the US share fell more because exports elsewhere grew",
                    "Confirmed if the rest-of-world side of the decline is larger than the US side",
                    label,
                    VARIANTS[variant],
                    "Rest-of-world share of the change",
                    r["row_share_of_change"],
                    0.5,
                    r["verdict"],
                ]
            )
    for baseline, label in analysis.BASELINES.items():
        r = analysis.h2(con, baseline)
        rows.append(
            [
                "H2: without gold and energy the decline is much smaller",
                f"Confirmed if the decline without gold and energy is at most "
                f"{t['h2_max_share_of_headline']:.0%} of the headline",
                label,
                "Without gold and energy ÷ all goods",
                "Ratio of declines (pp)",
                r["ratio"],
                r["limit"],
                r["verdict"],
            ]
        )
    for baseline, label in analysis.BASELINES.items():
        for r in analysis.h3(con, baseline):
            rows.append(
                [
                    "H3: tariffed sectors did not redirect to other markets",
                    f"Offset ratio: confirmed below {t['h3_offset_ratio_confirm_below']}, "
                    f"rejected above {t['h3_offset_ratio_reject_above']}, partial between",
                    label,
                    f"{r['label']} ({r['window_start']:%b %Y}–{r['window_end']:%b %Y})",
                    "Offset ratio",
                    r["offset_ratio"],
                    f"{t['h3_offset_ratio_confirm_below']} / {t['h3_offset_ratio_reject_above']}",
                    r["verdict"],
                ]
            )
    for baseline, label in analysis.BASELINES.items():
        for r in analysis.h4(con, baseline):
            rows.append(
                [
                    "H4: new non-US product × country pairs did not rise above the "
                    "pre-tariff level",
                    f"Confirmed if the latest count is within ±{t['h4_band']:.0%} of the baseline "
                    f"mean; rejected if above",
                    f"{label} (snapshots: {r['baseline_snapshots']})",
                    VARIANTS[r["variant"]],
                    "Change in count vs baseline mean",
                    r["change_vs_baseline"],
                    r["band"],
                    r["verdict"],
                ]
            )
    for i, row in enumerate(rows, start=5):
        for j, value in enumerate(row, start=1):
            cell = ws.cell(row=i, column=j, value=value)
            cell.alignment = WRAP
        measure = row[4]
        fmt = "0.000" if measure == "Offset ratio" else "0.0%"
        ws.cell(row=i, column=6).number_format = fmt
        if isinstance(row[6], float):
            ws.cell(row=i, column=7).number_format = "0%"
    widths(ws, {"A": 36, "B": 40, "C": 30, "D": 34, "E": 30, "F": 11, "G": 12, "H": 34})

    # Waterfall components.
    r0 = len(rows) + 7
    ws.cell(row=r0, column=1, value="Waterfall: change in the US share (pp)").font = BOLD
    header(
        ws,
        r0 + 1,
        [
            "Baseline",
            "US share, baseline (%)",
            "US share, latest (%)",
            "Total change (pp)",
            "Gold (pp, average of orders)",
            "Energy (pp, average of orders)",
            "Everything else (pp)",
        ],
    )
    for k, (baseline, label) in enumerate(analysis.BASELINES.items(), start=r0 + 2):
        w = analysis.waterfall(con, baseline)
        values = [
            label,
            w["s_base_pct"],
            w["s_tariff_pct"],
            w["total"],
            w["gold"],
            w["energy"],
            w["rest"],
        ]
        for j, value in enumerate(values, start=1):
            ws.cell(row=k, column=j, value=value)
            if j > 1:
                ws.cell(row=k, column=j).number_format = "0.00"
    note = r0 + 5
    ws.cell(
        row=note,
        column=1,
        value=(
            "H3 offset ratio = change in exports to other countries ÷ |change in exports to the "
            "US|, defined only when exports to the US fell. H4 uses the frozen baseline snapshots "
            "(Dec 2023 and Dec 2024) for both baselines. See README.md and docs/methodology.md."
        ),
    ).font = MUTED
    # H4 context rows: shown for transparency, never verdicts.
    c0 = note + 2
    ws.cell(row=c0, column=1, value="H4 context (not verdicts)").font = BOLD
    header(ws, c0 + 1, ["Kind", "Description", "Variant", "Count", "Reference", "Change"])
    rows_ctx = analysis.records(
        con, "select * from mart_extensive_margin_context order by kind, variant"
    )
    for k, r in enumerate(rows_ctx, start=c0 + 2):
        values = [
            r["kind"],
            r["description"],
            VARIANTS[r["variant"]],
            r["n_new_pairs"],
            r["reference"],
            r["change_vs_reference"],
        ]
        for j, value in enumerate(values, start=1):
            ws.cell(row=k, column=j, value=value).alignment = WRAP
        ws.cell(row=k, column=5).number_format = "0.0"
        ws.cell(row=k, column=6).number_format = "0.0%"
    ws.freeze_panes = "A5"


def exposure_sheet(wb, con) -> None:
    ws = wb.create_sheet("Sector exposure")
    cols = [
        "Baseline",
        "Sector",
        "Tariffed sector",
        "Exports, baseline (CAD)",
        "Exports, latest 12 months (CAD)",
        "Share of exports, baseline",
        "Share of exports, latest",
        "US dependence, baseline",
        "US dependence, latest",
        "US dependence change (pp)",
        "Destination HHI, baseline",
        "Destination HHI, latest",
        "Full tariff scope, latest",
        "Partial tariff scope, latest",
        "No tariff scope, latest",
    ]
    header(ws, 1, cols)
    row = 2
    for baseline, label in analysis.BASELINES.items():
        for r in analysis.exposure(con, baseline):
            values = [
                label,
                SECTOR_NAMES[r["sector_group"]],
                "yes" if r["is_tariffed_sector"] else "no",
                r["x_sector_base"],
                r["x_sector_latest"],
                r["share_of_exports_base"],
                r["share_of_exports_latest"],
                r["us_dependence_base"],
                r["us_dependence_latest"],
                r["us_dependence_change_pp"],
                r["hhi_base"],
                r["hhi_latest"],
                r["share_full_scope"],
                r["share_partial_scope"],
                r["share_no_scope"],
            ]
            for j, value in enumerate(values, start=1):
                ws.cell(row=row, column=j, value=value)
            for j in (4, 5):
                ws.cell(row=row, column=j).number_format = "#,##0"
            for j in (6, 7, 8, 9, 13, 14, 15):
                ws.cell(row=row, column=j).number_format = "0.0%"
            for j in (10, 11, 12):
                ws.cell(row=row, column=j).number_format = "0.00"
            row += 1
    widths(ws, {get_column_letter(i): 16 for i in range(1, len(cols) + 1)})
    ws.row_dimensions[1].height = 45
    ws.freeze_panes = "C2"
    ws.cell(
        row=row + 1,
        column=1,
        value=(
            "Ordered by US dependence in the latest 12 months within each baseline. US dependence "
            "= exports to the US ÷ the sector's exports. HHI = sum of squared destination shares. "
            "Source: mart_exposure."
        ),
    ).font = MUTED


def data_sheet(wb, con) -> None:
    """Pivot-ready long table: tariffed-sector exports by HS6, destination and period."""
    ws = wb.create_sheet("Data")
    rows = analysis.records(
        con,
        """
        select r.baseline, r.sector_group, d.hs2, d.hs4, r.code as hs6, d.description,
               r.window_start, r.window_end, r.n_months,
               r.x_us_base, r.x_us_tariff, r.x_nonus_base, r.x_nonus_tariff
        from mart_redirection r
        join dim_product d on d.hs6 = r.code
        where r.level = 'hs6'
        order by r.baseline, r.sector_group, r.code
        """,
    )
    if not rows:
        raise PipelineError("mart_redirection has no HS6 rows: run `make marts` first.")
    cols = [
        "baseline",
        "sector",
        "hs2",
        "hs4",
        "hs6",
        "description",
        "window_start",
        "window_end",
        "months_in_window",
        "destination",
        "period",
        "value_cad",
    ]
    header(ws, 1, cols)
    i = 2
    for r in rows:
        for destination, period, key in [
            ("United States", "Baseline", "x_us_base"),
            ("United States", "Latest window", "x_us_tariff"),
            ("Other countries", "Baseline", "x_nonus_base"),
            ("Other countries", "Latest window", "x_nonus_tariff"),
        ]:
            values = [
                analysis.BASELINES[r["baseline"]],
                analysis.SECTORS[r["sector_group"]],
                r["hs2"],
                r["hs4"],
                r["hs6"],
                r["description"],
                r["window_start"],
                r["window_end"],
                r["n_months"],
                destination,
                period,
                r[key],
            ]
            for j, value in enumerate(values, start=1):
                ws.cell(row=i, column=j, value=value)
            ws.cell(row=i, column=7).number_format = "yyyy-mm"
            ws.cell(row=i, column=8).number_format = "yyyy-mm"
            ws.cell(row=i, column=12).number_format = "#,##0"
            i += 1
    table = Table(
        displayName="TariffedSectorExports", ref=f"A1:{get_column_letter(len(cols))}{i - 1}"
    )
    table.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=True)
    ws.add_table(table)
    widths(
        ws,
        {
            "A": 12,
            "B": 16,
            "C": 6,
            "D": 7,
            "E": 9,
            "F": 50,
            "G": 12,
            "H": 12,
            "I": 10,
            "J": 16,
            "K": 14,
            "L": 16,
        },
    )
    ws.freeze_panes = "A2"
    notes = wb["Summary"]
    first = notes.max_row + 2
    notes.cell(row=first, column=1, value="About the Data sheet").font = BOLD
    for k, text in enumerate(
        [
            "Data sheet: exports of the five tariffed sectors by HS6 product, destination and "
            "period (source: mart_redirection, HS6 level).",
            "Each row is one product × destination × period for one baseline. Filter on one "
            "baseline before adding values: the 2022–2024 and 2023–2024 rows describe the same "
            "exports with different baselines.",
            "Latest window: the sector's tariff window (latest 12 months; softwood lumber from its "
            "first full tariff month). Baseline: the same calendar months averaged over the "
            "baseline years, without Nov 2024–Feb 2025.",
            "value_cad: Canadian dollars, customs basis (Statistics Canada CIMT domestic exports).",
        ],
        start=first + 1,
    ):
        notes.cell(row=k, column=1, value=text).font = MUTED


def parse_sources() -> list[list[str]]:
    rows, group = [], None
    for block in (DOCS / "sources.md").read_text(encoding="utf-8").split("\n\n"):
        block = block.strip()
        if block.startswith("## "):
            group = block[3:].strip()
            continue
        if group is None or block.startswith("#") or "http" not in block:
            continue
        url = re.search(r"https?://\S+", block).group(0).rstrip(".,)")
        accessed = re.search(r"\(accessed ([^)]*)\)", block)
        tier = re.search(r"\*\*Tier[^*]*\*\*", block)
        if not accessed or not tier:
            raise PipelineError(f"Source entry without access date or tier: {block[:80]!r}")
        reference = block[: block.index(url)].strip().replace("*", "").replace("`", "")
        rows.append(
            [
                group,
                reference,
                url,
                accessed.group(1),
                tier.group(0).strip("*").rstrip("."),
            ]
        )
    if not rows:
        raise PipelineError("No entries parsed from docs/sources.md")
    return rows


def sources_sheet(wb) -> None:
    ws = wb.create_sheet("Sources")
    header(ws, 1, ["Group", "Reference (APA 7)", "URL", "Accessed", "Tier"])
    for i, row in enumerate(parse_sources(), start=2):
        for j, value in enumerate(row, start=1):
            cell = ws.cell(row=i, column=j, value=value)
            cell.alignment = WRAP
    widths(ws, {"A": 18, "B": 80, "C": 60, "D": 24, "E": 22})
    ws.freeze_panes = "A2"


def main() -> None:
    con = analysis.connect()
    wb = Workbook()
    wb.properties.creator = "Omar Serrano"
    wb.properties.title = "Canada export diversification under US tariffs: analyst pack"
    summary_sheet(wb, con)
    exposure_sheet(wb, con)
    data_sheet(wb, con)
    sources_sheet(wb)
    con.close()
    OUT.parent.mkdir(exist_ok=True)
    wb.save(OUT)
    print(f"  {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
