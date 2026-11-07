# Data dictionary

Tables live in `data/processed/trade.duckdb`. Marts are also exported as CSV to `data/processed/csv/`.
Model: raw files → landing CSVs → staging tables (`sql/staging_*.sql`) → marts (`sql/mart_*.sql`).

## fact_exports

**Grain:** month × country × HS6.

Canada's domestic exports, summed over provinces and US states. `value_cad` in Canadian dollars. `quantity` in `qty_unit` (HS 2710 hectolitres converted to litres). `country_code` is the StatCan CIMT code (ISO alpha-2). `vintage_date` is the CIMT download date. Source: StatCan CIMT bulk files.

Columns: `month` (date), `country_code` (varchar), `country_iso3` (varchar), `hs6` (varchar), `value_cad` (double), `quantity` (double), `qty_unit` (varchar), `flow` (varchar), `source` (varchar), `vintage_date` (date)

## dim_country

**Grain:** country.

`ptp_group` follows StatCan Principal Trading Partners: United States, European Union (27 members, config/eu_members.csv), United Kingdom, China, Japan, Mexico, South Korea, Rest of world. ISO alpha-3 from StatCan SCCAI 2019.

Columns: `country_code` (varchar), `country_iso3` (varchar), `name` (varchar), `ptp_group` (varchar), `is_us` (boolean)

## dim_product

**Grain:** HS6.

`sector_group`: steel, aluminum, copper, autos, lumber (the five tariffed sectors), gold (HS 7108), energy (HS 27), other. Rules in config/settings.yaml (`sectors`). `is_tariffed` = one of the five sectors. `is_steel_primary` / `is_aluminum_primary` = Proclamation 9705 / 9704 definitions. Description from the StatCan HS6 file; `hs2_description` from the StatCan HS2 file (ODPF_5_HS2Desc).

Columns: `hs6` (varchar), `hs4` (varchar), `hs2` (varchar), `description` (varchar), `hs2_description` (varchar), `default_unit` (varchar), `sector_group` (varchar), `is_gold` (boolean), `is_energy` (boolean), `is_crude` (boolean), `is_steel_primary` (boolean), `is_aluminum_primary` (boolean), `is_softwood_lumber` (boolean), `is_tariffed` (boolean)

## dim_month

**Grain:** month.

`period_label`: baseline (2022–2024 without front-loading months), frontload (Nov 2024–Feb 2025), transition, tariff (latest 12 months). `in_baseline` / `in_sensitivity_baseline` mark the primary (2022–2024) and sensitivity (2023–2024) baselines.

Columns: `month` (date), `month_label` (varchar), `calendar_month` (bigint), `period_label` (varchar), `in_sensitivity_baseline` (boolean), `in_baseline` (boolean), `is_latest` (boolean)

## tariff_events

**Grain:** event × HS scope.

US tariff measures on Canadian goods (config/tariff_events.csv). Every row cites a Tier 1 `source_url`. `rate_pct` is the headline additional duty.

Columns: `event_id` (varchar), `event_date` (date), `hs_scope` (varchar), `sector_group` (varchar), `measure` (varchar), `legal_basis` (varchar), `rate_pct` (double), `usmca_treatment` (varchar), `notes` (varchar), `document` (varchar), `source_url` (varchar), `access_date` (date)

## tariff_lists

**Grain:** official list.

Official US product lists (CBP attachments, proclamation annexes) used to build tariff scope (config/tariff_lists.csv). `series_mode`: cumulative (lists add lines) or replace (the newest list replaces the older one). `value_basis`: full_value, metal_content or non_us_content.

Columns: `list_id` (varchar), `event_id` (varchar), `effective_date` (date), `series` (varchar), `series_mode` (varchar), `sector_group` (varchar), `value_basis` (varchar), `usmca_exempt` (boolean), `url` (varchar)

## staging_tariff_scope_monthly

**Grain:** HS6 × month.

`tariff_scope`: full / partial / none (see docs/methodology.md). `measures` lists the measures in force (list ids or rule ids).

Columns: `month` (date), `hs6` (varchar), `tariff_scope` (varchar), `measures` (varchar)

## prices

**Grain:** month × series.

World Bank Pink Sheet monthly prices in USD: gold ($/troy oz), crude oil average, Brent, WTI ($/bbl).

Columns: `month` (date), `series` (varchar), `value` (double)

## fx

**Grain:** month.

Bank of Canada FXMUSDCAD: monthly average of one US dollar in Canadian dollars.

Columns: `month` (date), `usdcad` (double)

## mart_us_share

**Grain:** month × variant.

M1. Variants: total, ex_gold, ex_energy, ex_gold_ex_energy. `*_12m` = rolling 12-month sums (null until 12 months exist). `us_share_12m` = X_US / (X_US + X_RoW). `*_yoy` = year-over-year change of the monthly value. `*_usd` = same in US dollars.

Columns: `month` (date), `period_label` (varchar), `variant` (varchar), `x_us` (double), `x_row` (double), `x_us_yoy` (double), `x_row_yoy` (double), `x_us_12m` (double), `x_row_12m` (double), `us_share_12m` (double), `x_us_12m_usd` (double), `x_row_12m_usd` (double), `us_share_12m_usd` (double)

## mart_decomposition

**Grain:** baseline × variant.

M2 (H1). Baseline = calendar-month average annual equivalent; tariff = latest 12 months. `us_side_*` and `row_side_*` are the US-side and RoW-side contributions to the change in ln(US share). `method_used` says which form applies under the frozen 10% residual rule.

Columns: `baseline` (varchar), `variant` (varchar), `x_us_base` (double), `x_row_base` (double), `x_us_tariff` (double), `x_row_tariff` (double), `s_us_base` (double), `s_us_tariff` (double), `d_share_pp` (double), `dln_x_us` (double), `dln_x_row` (double), `dln_s_us` (double), `w_row_base` (double), `us_side_approx` (double), `row_side_approx` (double), `total_approx` (double), `approx_residual` (double), `approx_residual_share` (double), `w_row_logmean` (double), `us_side_exact` (double), `row_side_exact` (double), `method_used` (varchar)

## mart_waterfall

**Grain:** baseline × component.

M3 (H2). Change in the US share in percentage points split into gold, energy and everything else. `effect_pp` = average of the two removal orders.

Columns: `baseline` (varchar), `step` (integer), `component` (varchar), `order_gold_first` (double), `order_energy_first` (double), `effect_pp` (double), `s_total_base_pct` (double), `s_total_tariff_pct` (double)

## mart_price_volume

**Grain:** baseline × commodity × destination.

M4. Gold and crude: value, quantity, unit value; `price_effect` + `volume_effect` = `d_value` (midpoint split).

Columns: `baseline` (varchar), `commodity` (varchar), `destination` (varchar), `v_base` (double), `q_base` (double), `p_base` (double), `v_tariff` (double), `q_tariff` (double), `p_tariff` (double), `d_value` (double), `price_effect` (double), `volume_effect` (double)

## mart_price_volume_monthly

**Grain:** month × commodity × destination.

M4 monthly: unit value vs World Bank benchmark price converted to CAD per unit (gram for gold, cubic metre for crude).

Columns: `month` (date), `commodity` (varchar), `destination` (varchar), `value_cad` (double), `quantity` (double), `qty_unit` (varchar), `unit_value_cad` (double), `benchmark_cad_per_unit` (double), `usdcad` (double)

## mart_hhi

**Grain:** window × variant.

M5. `window_type` rolling_12m (by month) or period (primary, sensitivity, tariff). HHI, effective number of markets, and the same within non-US exports.

Columns: `window_type` (varchar), `window_label` (varchar), `month` (date), `variant` (varchar), `hhi` (double), `n_eff` (double), `hhi_ex_us` (double), `n_eff_ex_us` (double), `us_share` (double)

## mart_redirection

**Grain:** baseline × level × code.

M6 (H3) for the five tariffed sectors at sector, HS4 and HS6 level. Window per sector (see sector start dates). `offset_ratio` only when US exports fell.

Columns: `baseline` (varchar), `level` (varchar), `sector_group` (varchar), `code` (varchar), `window_start` (date), `window_end` (date), `n_months` (bigint), `x_us_base` (double), `x_us_tariff` (double), `x_nonus_base` (double), `x_nonus_tariff` (double), `d_us` (double), `d_nonus` (double), `d_us_pct` (double), `d_nonus_pct` (double), `offset_ratio` (double)

## mart_redirection_no_sector_tariff

**Grain:** baseline × sector window × variant.

M6 comparison group "no sector-specific tariff": products outside the five sectors with tariff scope none in that month, over each sector's window. Percent changes toward the US and the rest of the world are reported next to the offset ratio.

Columns: `baseline` (varchar), `window_of_sector` (varchar), `group_variant` (varchar), `window_start` (date), `window_end` (date), `x_us_base` (double), `x_us_tariff` (double), `x_nonus_base` (double), `x_nonus_tariff` (double), `d_us` (double), `d_nonus` (double), `d_us_pct` (double), `d_nonus_pct` (double), `offset_ratio` (double)

## mart_extensive_margin

**Grain:** snapshot × variant.

M7 (H4). Number of new HS6 × non-US country pairs at each snapshot. `role`: baseline, tariff (latest month) or post_hoc (latest December, context only).

Columns: `snapshot` (date), `role` (varchar), `variant` (varchar), `n_new_pairs` (bigint)

## mart_extensive_margin_pairs

**Grain:** snapshot × pair.

M7 detail: the pairs counted as new, with their prior and current rolling 12-month sums.

Columns: `snapshot` (date), `role` (varchar), `hs6` (varchar), `country_code` (varchar), `is_gold` (boolean), `is_energy` (boolean), `prior_r12` (double), `r12` (double), `min_r12_last3` (double)

## mart_extensive_margin_test

**Grain:** baseline × variant.

H4 test inputs (frozen rule). Both baselines use the frozen baseline snapshots (Dec 2023 and Dec 2024). `change_vs_baseline` = latest count ÷ baseline mean − 1.

Columns: `baseline` (varchar), `variant` (varchar), `baseline_snapshots` (varchar), `n_baseline_snapshots` (bigint), `baseline_mean` (double), `tariff_snapshot` (date), `tariff_count` (bigint), `change_vs_baseline` (double)

## mart_extensive_margin_context

**Grain:** kind × variant.

Context for H4, never a verdict. `exploratory`: latest count vs the Dec 2024 snapshot alone (defined after seeing the result). `post_hoc`: count at the latest December (same calendar month as the baseline snapshots) vs the frozen baseline mean.

Columns: `kind` (varchar), `description` (varchar), `reference_label` (varchar), `variant` (varchar), `snapshot` (date), `n_new_pairs` (bigint), `reference` (double), `change_vs_reference` (double)

## mart_extensive_margin_by_group

**Grain:** snapshot × dimension (country or HS2) × code.

Where the new pairs are: count of new pairs by destination country and by HS2 chapter at each snapshot, the count without gold and energy, the number of gold pairs (HS 7108) and of chapter 71 pairs, the baseline mean for the same country or chapter, the change against that mean, and the rank within the snapshot (ties share a rank).

Columns: `snapshot` (date), `role` (varchar), `dimension` (varchar), `code` (varchar), `label` (varchar), `n_new_pairs` (bigint), `n_new_pairs_ex_gold_ex_energy` (bigint), `n_gold` (bigint), `n_hs2_71` (bigint), `baseline_mean` (double), `change_vs_baseline_mean` (double), `rank_in_snapshot` (bigint)

## mart_frontload_check

**Grain:** variant × destination.

Exports Nov 2024–Feb 2025 vs Nov 2023–Feb 2024, to measure front-loading outside the US (bias check for M7).

Columns: `variant` (varchar), `destination` (varchar), `year_before` (double), `frontload` (double), `change_pct` (double)

## mart_exposure

**Grain:** baseline × sector group.

M8. Share of Canada's exports, US dependence (baseline vs latest 12 months), destination HHI, and the share of latest exports under full / partial / no tariff scope.

Columns: `baseline` (varchar), `sector_group` (varchar), `is_tariffed_sector` (boolean), `x_sector_base` (double), `x_sector_latest` (double), `share_of_exports_base` (double), `share_of_exports_latest` (double), `us_dependence_base` (double), `us_dependence_latest` (double), `us_dependence_change_pp` (double), `hhi_base` (double), `hhi_latest` (double), `share_full_scope` (double), `share_partial_scope` (double), `share_no_scope` (double)
