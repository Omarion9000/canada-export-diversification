# Methodology

This file explains each method in plain words. Every method should fit in two plain sentences.
Settings and thresholds live in `config/settings.yaml` and were frozen on 2026-11-06, before analysis.

## Data

- **Source.** Statistics Canada, Canadian International Merchandise Trade (CIMT) bulk files, domestic exports, HS6 level, monthly, January 2022 onward.
- **Domestic exports.** These are goods grown, extracted or made in Canada. Re-exports (foreign goods shipped out again) are excluded.
- **Customs basis.** Values are recorded when goods cross the border, in Canadian dollars. Exports to the United States are measured with US import data under the Canada–US data exchange.
- **Classification.** All months use HS2022. The HS (Harmonized System) is the world standard list of product codes; HS6 is its 6-digit level.
- **Unit change.** For HS 2710 (refined petroleum), quantities switch from hectolitres to litres in January 2026. Staging converts hectolitres to litres (× 100) so the series is continuous.
- **Vintage and reruns.** Each run downloads the sources again, but a new copy is kept only if its bytes differ from the latest saved copy. The vintage (download date) is therefore the date the current data were first downloaded, and a rerun on unchanged data gives identical outputs. Marts are built with one thread so float sums are identical between runs; CSV exports are sorted and rounded (10 decimals, at most 12 significant digits).

## Periods

- **Baseline.** 2022–2024 (primary) and 2023–2024 (sensitivity).
- **Front-loading window.** November 2024 to February 2025. Front-loading means firms shipped early to beat expected tariffs. These months are excluded from both the baseline and the tariff period in headline comparisons.
- **Tariff period.** The latest rolling 12 months that start no earlier than March 2025.
- **H3 sector timing.** Each tariffed sector's tariff period starts at its own first event (see `h3_sector_start` in the settings), not at one common date.

## Sector definitions and tariff scope

Sector groups and the `tariff_scope` column (full / partial / none) follow the official US documents, not whole HS chapters.

- **Steel.** "Full" covers the HS6 ranges in Proclamation 9705. Other lines in HS 7206–7229 and 7301–7326 are "partial" (derivatives). HS 7201–7205 (pig iron, ferro-alloys, scrap) are outside Section 232 and go to "other".
- **Aluminum.** "Full" covers HS 7601 and 7604–7609 (Proclamation 9704). Derivatives (7610, 7614–7616) are "partial".
- **Copper.** Lines in the Proclamation 10962 annex are "partial", because the duty applies to copper content. HS 7401–7405, including 7403 refined copper, are not covered and go to "other".
- **Autos and parts.** All covered lines are "partial", because USMCA rules exempt part of the value (US content for vehicles, USMCA-qualifying parts).
- **Lumber.** Softwood lumber (HS 4407.11–4407.19) is "full". Other lines in the Proclamation 10976 annex are "partial".

## M7: extensive margin (frozen)

The extensive margin counts new trade flows: an HS6 product sold to a non-US country where Canada sold little or nothing before.

**Rule.** A product × country pair is "new" at a snapshot month when both conditions hold:
1. The rolling 12-month sum that ended 12 months earlier is below CAD 100,000.
2. The rolling 12-month sum is above CAD 1,000,000 at three consecutive month-ends: the snapshot month and the two months before it.

**Baseline snapshots.** December 2023 (2023 vs 2022) and December 2024 (2024 vs 2023). The data start in January 2022, so December is the first month with a full prior 12-month window inside HS2022 data.

| Snapshot | New pairs (full rule) |
|---|---|
| 2023-12 | 516 |
| 2024-12 | 495 |
| Baseline mean | 505.5 |

These counts were computed during the design phase from the 2022–2024 files only.

**Both baselines use the frozen snapshots.** The H4 verdict uses the mean of the frozen baseline snapshots (December 2023 and December 2024) for both the 2022–2024 and the 2023–2024 baselines, as the frozen rule says. The two verdicts are therefore the same.

**Context, not verdicts (`mart_extensive_margin_context`).**
- *Exploratory, defined after seeing the result:* the latest count against the December 2024 snapshot alone (495 pairs). It was set at Gate 4 (2026-11-06), when the latest count was already known, so it is reported as context only.
- *Post hoc robustness:* the count at the latest December (December 2025), the same calendar month as the baseline snapshots, against the frozen baseline mean. Context only; it does not change the verdict.

**Where the new pairs are.** New pairs are also counted by destination country and by HS2 chapter (`mart_extensive_margin_by_group`). Chapter names are Statistics Canada's HS2 descriptions from the CIMT bulk files.

**Note on a recon error.** During recon (2026-11-06), a threshold sensitivity table also computed annual counts for 2025 by mistake. Those 2025 counts were never reviewed or used to choose thresholds, and they are not reported anywhere. Counts for 2025–2026 are first computed in the analysis phase, after the thresholds were frozen.

## Baseline values

A baseline value is the average of each calendar month over the baseline years, added up over the 12 calendar months. Because the front-loading months (November and December 2024) are left out, November and December are averaged over two years instead of three, and every calendar month still counts once.

This keeps seasons balanced: dropping two winter months does not make the baseline look like a year with less winter in it.

## Tariff scope by product and month

`staging_tariff_scope_monthly` gives each HS6 product a scope in each month: full, partial or none.

- **Sources.** Official US lists: CBP attachments to CSMS messages and proclamation annexes (`config/tariff_lists.csv`). The USITC HTS export lists every US 8-digit tariff line. The definitions in Proclamations 9704 and 9705 cover primary steel and aluminum. The softwood lumber AD/CVD orders cover HS 4407.11–4407.19 for the whole period.
- **Full.** A measure covers every US tariff line of the HS6 code, on the full value, with no USMCA exemption.
- **Partial.** A measure covers only some lines, or taxes only part of the value (metal content, non-US content), or exempts USMCA goods.
- **Timing.** A measure counts in a month if it takes effect on or before the last day of that month. Steel and aluminum derivative lists add up over time. Each Section 338 list replaces the one before it.
- **What is left out.** Across-the-board measures (IEEPA from March 2025 to February 2026, the Section 122 surcharge in February–July 2026, Section 301 from July 2026) apply to all non-USMCA goods. They do not separate products with and without a sector-specific tariff, so they are not used for scope.
- **Section 338 example.** Passenger vehicles in HS 8703.22–8703.24 stay "partial" (autos Section 232 with USMCA content rules). The Section 338 list of 2026-09-15 adds only HS 8703.10.50 and 8703.21.01, so only HS 870321 becomes "full", from September 2026.

## H3: redirection windows

Each tariffed sector's window starts at the first full month on or after its first event: steel and aluminum April 2025, autos May 2025, copper August 2025, lumber November 2025.

When 12 or more months are available, the window is the latest 12 months. For lumber only 11 months exist (November 2025 to September 2026), so lumber is compared with the baseline average of the same calendar months (November to September).

The comparison group "no sector-specific tariff" is built month by month: products outside the five sectors whose tariff scope is "none" in that month. For this group and for each sector, the mart also reports the percent change in exports to the US and to the rest of the world, next to the offset ratio. The offset ratio exists only when US exports fell.

## Limitations

- **General tariffs in the comparison group.** From March 2025 to February 2026, goods that did not qualify for USMCA paid the across-the-board IEEPA duties even when they sit in the "no sector-specific tariff" group. The group is free of sector-specific measures, not of all US tariffs.
- **Lumber timing.** Softwood lumber already paid US anti-dumping and countervailing duties before 2025. Those duties rose in July–August 2025: for non-selected companies, anti-dumping went from 7.66% to 20.56% and countervailing from 6.74% to 14.63% (2022 and 2023 review results). The before-and-after comparison for lumber is therefore less clean than for the other sectors.
- **M7 and front-loading.** The tariff-period snapshot (latest month) compares against a prior 12-month window that includes the front-loading months. If that prior window is inflated, fewer pairs look new, which pushes the H4 test toward confirmation. `mart_frontload_check` measures the size of front-loading: from November 2024 to February 2025, exports grew 3.5% to non-US destinations and 9.9% to the US compared with one year earlier (3.2% and 5.5% without gold and energy). Front-loading outside the US was small, so this bias should also be small.
- **Section 232 metals after April 2026.** Proclamation 11021 moved the metal tariffs to the full customs value from 2026-04-06. Its annexes are scanned images, so scope keeps the 2025 lists; derivative lines stay "partial".
- **Import bans.** Proclamations 11061–11063 ban some Canadian products from 2026-09-29. Their product lists were not verified, so they are not in the scope table. They affect only the last two days of the data.
- **AD/CVD scope.** The softwood lumber order scope is approximated by HS 4407.11–4407.19. The order's HTS list was not verified line by line.
- **US HTS release.** Line coverage uses the current USITC HTS release. Lines that changed earlier are compared with today's line structure.

## Validation

- **V1a.** Annual total exports by country from CIMT vs StatCan table 12-10-0171-01 (independent StatCan publication).
- **V1b.** Monthly domestic exports by principal trading partner from CIMT vs StatCan table 12-10-0182-01. This is a consistency test: both come from the same StatCan source, so it is not an independent validation.
- **V1-EU.** CIMT total exports to the 27 EU members vs the "European Union" series in 12-10-0011-01. This confirms the member list (CETA preamble, minus the United Kingdom from January 2021 as stated in the 12-10-0011-01 footnote).
- **V4.** The Daily and the Global Affairs Canada reports are text. V4 uses the StatCan tables behind them instead: 12-10-0011-01 for total exports and 12-10-0182-01 for gold.
- **Country names.** StatCan tables and CIMT spell some countries differently ("South Korea" vs "Korea, South"). `config/statcan_partner_crosswalk.csv` lists each pair.

Other validators (V2–V6) are described in `docs/validation_report.md`.
