# Tableau data guide

The dashboard reads the CSV files that `make all` writes to `data/processed/csv/` (one file per mart, plus four dimension tables). Every value comes from Statistics Canada CIMT domestic exports (customs basis) unless a field says otherwise. Money is in Canadian dollars (CAD); shares and percent changes are stored as ratios (0.25 = 25%).

## The published dashboard

The workbook `tableau/canada_export_diversification.twbx` is the dashboard on [Tableau Public](https://public.tableau.com/app/profile/omar.serrano/viz/DidCanadareallydiversifyitsexportsawayfromtheUS/Dashboard1) (screenshot: `tableau/screenshots/dashboard.png`). It uses four CSV files, each loaded as an extract packaged inside the `.twbx`:

| Dashboard view | CSV |
|---|---|
| Waterfall: gold, energy, everything else | `tableau_waterfall.csv` |
| US share over time | `mart_us_share.csv` |
| Redirection by tariffed sector (H3) | `mart_redirection.csv` |
| Sector exposure (M8) | `mart_exposure.csv` |

The extracts are snapshots of these CSV files. After `make all` changes the data, refresh the extracts in Tableau and save the `.twbx` again. Loose `.hyper` and `.twb` files are not committed.

## Which CSV feeds which view

| View | CSV | Key fields | Notes |
|---|---|---|---|
| US share over time (line) | `mart_us_share.csv` | `month`, `variant`, `us_share_12m` | Filter `variant` to `total` and `ex_gold_ex_energy`. `us_share_12m` is empty for the first 11 months (12-month sums need 12 months). |
| Waterfall: gold, energy, everything else | `mart_waterfall.csv` | `baseline`, `step`, `component`, `effect_pp` | Filter `baseline = primary`. Sort by `step`. `effect_pp` is the average of the two removal orders; `order_gold_first` and `order_energy_first` give the range. Start and end bars: `s_total_base_pct`, `s_total_tariff_pct`. |
| Waterfall, ready to draw (recommended) | `tableau_waterfall.csv` | `baseline`, `bar_order`, `label`, `bar_start`, `bar_end`, `value_pp`, `kind` | Built from `mart_waterfall` in `make exports`. Five bars per baseline: 1 US share, baseline (level, from 0); 2 Gold; 3 Energy; 4 Everything else (each starts where the previous bar ended); 5 US share, latest 12 months (level, from 0). Values in % (76.2, not 0.762). `value_pp` = `bar_end` − `bar_start` (the share itself for level bars). `kind`: `level`, `decrease` or `increase`. Filter `baseline = primary`; draw a Gantt bar from `bar_start` with size `value_pp`, sorted by `bar_order`, colored by `kind`. |
| Which side moved (H1) | `mart_decomposition.csv` | `baseline`, `variant`, `us_side_exact`, `row_side_exact`, `method_used` | Use the `_exact` columns when `method_used = exact`, otherwise `_approx`. |
| Gold and crude, price vs volume | `mart_price_volume.csv` | `baseline`, `commodity`, `destination`, `price_effect`, `volume_effect`, `d_value` | Midpoint split; `price_effect + volume_effect = d_value`. Monthly unit values: `mart_price_volume_monthly.csv`. |
| Redirection by tariffed sector (H3) | `mart_redirection.csv` | `baseline`, `level`, `sector_group`, `code`, `d_us_pct`, `d_nonus_pct`, `offset_ratio` | `level` is `sector`, `hs4` or `hs6`: filter to one level before adding values. `offset_ratio` is empty when exports to the US did not fall. |
| Comparison group (H3) | `mart_redirection_no_sector_tariff.csv` | `baseline`, `window_of_sector`, `group_variant`, `d_us_pct`, `d_nonus_pct` | One row per sector window. Use `group_variant = ex_gold_ex_energy` next to the sectors. |
| New export pairs (H4) | `mart_extensive_margin.csv`, `mart_extensive_margin_test.csv` | `snapshot`, `role`, `variant`, `n_new_pairs`; `baseline_mean`, `tariff_count`, `change_vs_baseline` | Band = `baseline_mean` × (1 ± 0.20). Filter `role` to `baseline` and `tariff`; `post_hoc` rows and `mart_extensive_margin_context.csv` are context only, never verdicts. |
| Where the new pairs are (H4) | `mart_extensive_margin_by_group.csv` | `role`, `dimension`, `label`, `n_new_pairs`, `baseline_mean`, `rank_in_snapshot` | Filter `role = tariff` and `dimension` to `country` or `hs2`. Ties share a rank. Pair-level detail: `mart_extensive_margin_pairs.csv` (join `hs6` to `dim_product.csv`, `country_code` to `dim_country.csv`). |
| Sector exposure (M8) | `mart_exposure.csv` | `baseline`, `sector_group`, `us_dependence_base`, `us_dependence_latest`, `us_dependence_change_pp` | Filter `baseline = primary`. `us_dependence_change_pp` is already in percentage points. |
| Destination concentration | `mart_hhi.csv` | `window_label`, `variant`, `hhi`, `n_eff`, `hhi_ex_us` | `n_eff` = 1 ÷ HHI (the number of equal-sized destinations with the same concentration). |

## Field meanings

- `baseline`: `primary` = 2022–2024, `sensitivity` = 2023–2024. Baseline values average each calendar month over the baseline years and leave out November 2024 to February 2025 (front-loading).
- `variant`: `total` (all goods), `ex_gold` (without HS 7108), `ex_energy` (without HS 27), `ex_gold_ex_energy` (without both).
- `x_us`, `x_row`, `x_nonus`: exports to the United States and to all other countries (rest of world).
- `_base` / `_tariff` or `_latest`: baseline value / value in the latest window (latest 12 months, or the sector's own window in H3).
- `us_share_12m`: exports to the US ÷ all exports, 12-month sums. `_usd` columns convert with the Bank of Canada monthly USD/CAD rate (check only).
- `offset_ratio`: change in exports to other countries ÷ |change in exports to the US|.
- `sector_group`: `steel`, `aluminum`, `copper`, `autos` (autos and parts), `lumber` (softwood lumber), `gold`, `energy`, `other`.
- Dimension tables: `dim_product.csv` (HS6 → HS4, HS2, descriptions, sector), `dim_country.csv` (country code → name, ISO3, trading-partner group), `dim_month.csv` (month → baseline / front-loading / tariff label), `tariff_events.csv` (each US measure with its Tier 1 source URL).

## Source line for every view

Source: Statistics Canada, CIMT domestic exports (customs basis), Jan 2022–Sep 2026.
