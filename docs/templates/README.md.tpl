# Canada Export Diversification Under US Tariffs

**Short answer.** Since the 2025 US tariffs, the US share of Canada's goods exports fell by {d_total} percentage points, from {s_base}% to {s_latest}%. Gold accounts for {gold_share} of that drop ({d_gold} points), and most of the rise in gold exports is a price effect, not more gold shipped. Without gold and energy, the share fell only {d_rest} points, and that smaller drop is linked mostly to growth in exports to other countries, not to a fall in exports to the US.

**Where the diversification is.** Among the five sectors with US tariffs, {h3_rejected} redirected most of its US loss to other markets (offset ratio {alu_or}); {h3_confirmed} did not{h3_partial_clause}. Products with no sector-specific tariff sold {grp_us_abs}% {grp_us_dir} to the US, so the fall in US sales is concentrated in the tariffed sectors. New product–country pairs outside the US reached {h4_count}, {h4_change_abs}% above the baseline: {h4_short}, so a moderate rise cannot be ruled out. Against the baseline, new pairs rose most in {h4_risers}; {h4_hs2_leader} has the most new pairs.

![Waterfall of the change in the US share of Canada's exports](figures/h2_waterfall.png)

*Baseline 2022–2024 vs the latest 12 months ({tariff_start}–{tariff_end}). Gold and energy effects are the average of two removal orders.*

> Status: all four hypotheses tested (H1–H4) plus the sector exposure table. Data to {last_month}.

## The question

How much of the drop in the US share of Canada's goods exports since the 2025 US tariffs is genuine diversification, and how much is gold and energy? Where is the genuine diversification, if any?

"US share" means exports to the United States divided by all of Canada's goods exports. It can fall for two reasons: Canada sells less to the US, or Canada sells more to everyone else.

## Scope

- **Goods only.** Canada's domestic exports, meaning goods grown, mined or made in Canada. Re-exports (foreign goods shipped out again) are left out.
- **Monthly, {first_month} to {last_month}**, in Canadian dollars, by product (HS6, the 6-digit international product code) and destination country.
- **Baseline:** 2022–2024, with 2023–2024 as a check. **Tariff period:** the latest 12 months ({tariff_start}–{tariff_end}).
- **Front-loading left out.** November 2024 to February 2025 are excluded from both periods, because many firms shipped early to beat the expected tariffs.

**Out of scope:** causality, policy advice and forecasts; services; firm-level data; provinces; US or Mexican mirror data; and Canada's counter-tariffs on US goods (this project studies Canada's exports only).

## Data and validation

- **Main source:** Statistics Canada's Canadian International Merchandise Trade (CIMT) bulk files, at {n_hs6} product codes and {n_countries} destinations (data downloaded {vintage}).
- **Other sources:** Statistics Canada tables, World Bank commodity prices, Bank of Canada exchange rates, and {n_events} US tariff events taken from primary US government documents.
- **Checks before any result:** totals are compared with published Statistics Canada tables (by country, by year and by month), the customs-based US share is compared with the balance-of-payments figure, and gold prices per gram are compared with World Bank prices. All halting checks passed for this data download. Details: [docs/validation_report.md](docs/validation_report.md).

## Method in plain words

1. **US share.** For each month, add up the last 12 months of exports to the US and to all other countries, then divide. Twelve-month sums remove seasonal swings.
2. **Baseline.** Each calendar month is averaged over the baseline years, then the 12 months are added. This keeps seasons balanced even though two front-loading months are left out.
3. **Which side moved (H1).** The change in the share is split into a US part and a rest-of-world part, using a standard log decomposition. If the simple version is off by more than 10%, an exact version is used.
4. **Gold and energy (H2).** The share is recomputed without gold, and without gold and energy. The differences are the gold and energy effects. Both removal orders are computed and averaged.
5. **Price or volume.** For gold and crude oil, the change in export value is split into a price part and a quantity part, using the value per gram (or per cubic metre) from the customs data.
6. **Redirection (H3).** For each tariffed sector, the offset ratio divides the gain in exports to other countries by the loss in exports to the US. A ratio of 0.1 means 10 cents gained elsewhere for every dollar lost in the US. Each sector is measured from its own first tariff, against the same calendar months in the baseline.
7. **New export pairs (H4).** A product (HS6) and a non-US country form a new pair when exports go from under CAD 100,000 a year to over CAD 1 million a year, for three month-ends in a row. The count at the latest month is compared with the count at the end of 2023 and 2024.
8. **Sector exposure.** For each sector: the share of its exports that goes to the US, before and after, and how spread out its destinations are.

All thresholds were fixed before looking at results ([config/settings.yaml](config/settings.yaml)). Full details: [docs/methodology.md](docs/methodology.md).

## Findings

### H1 · Is the drop linked more to other markets growing than to US exports falling? **{h1_verdict_cap}**

- Exports to the US went from CAD {x_us_base} billion a year in the baseline to CAD {x_us_latest} billion in the latest 12 months ({us_growth}%).
- Exports to all other countries went from CAD {x_row_base} billion to CAD {x_row_latest} billion ({row_growth}%). Gold accounts for CAD {gold_row_change_bn} billion of that CAD {row_change_bn} billion increase ({gold_row_growth_share}).
- About {h1_row_share} of the change in the US share is on the rest-of-world side ({h1_row_side} log points vs {h1_us_side} for the US side; {h1_method} form). The rule was: confirmed if the rest-of-world side is larger.
- Without gold and energy, exports to other countries changed {row_growth_x}% and exports to the US {us_growth_x}%. The rest-of-world side is still larger ({h1_row_share_x} of the change): **{h1_verdict_x}**.
- With the 2023–2024 baseline the results are {h1_same}: {h1_row_share_sens} (all goods) and {h1_row_share_x_sens} (without gold and energy) on the rest-of-world side.

![US share of Canada's exports, 12-month sums](figures/m1_us_share.png)

### H2 · Without gold and energy, is the drop much smaller? **{h2_verdict_cap}**

**Two parts to the answer.**

1. **Gold explains {gold_part} of the drop.** The US share changed {d_total_s} pp in total: gold {d_gold_s} pp ({gold_share} of the drop), energy {d_energy_s} pp on average, everything else {d_rest_s} pp ({rest_share}). Shares may not sum to 100% due to rounding.
2. **Without gold and energy, the US share still fell {d_rest} points.** That smaller drop is linked mostly to higher sales to other countries ({h1_row_share_x} of it is on the rest-of-world side; see H1), not to lower sales to the US.

- **Verdict.** The rule was: confirmed if the drop without gold and energy is at most {h2_limit} of the headline drop. It is {h2_ratio}.
- **Sensitivity.** With the 2023–2024 baseline, the verdict is {h2_same} ({h2_verdict_sens}){thin_clause}: the drop without gold and energy is {h2_ratio_sens} of the headline (threshold {h2_limit}). The share fell {d_total_sens} points: gold {d_gold_sens_s} pp, energy {d_energy_sens} pp, everything else {d_rest_sens_s} pp.
- **Removal order.** The gold effect ranges from {gold_lo_s} to {gold_hi_s} pp and the energy effect from {energy_lo} to {energy_hi} pp, depending on which is removed first. The average of both orders is reported.
- **Price or volume?** Gold exports to other countries {g_row_dir} by CAD {g_row_dv} billion a year. {g_row_price_share} of that change (CAD {g_row_pe} billion) is a price effect: the value per gram changed {g_row_p}% and grams shipped {g_row_q}%. Gold exports to the US {g_us_dir} by CAD {g_us_dv} billion, with a volume effect of CAD {g_us_ve_s} billion (grams {g_us_q}%). Crude oil exports to other countries {c_row_dir} by CAD {c_row_dv} billion, mostly {c_row_main} (volume effect CAD {c_row_ve_s} billion); crude to the US {c_us_dir} by CAD {c_us_dv} billion, mostly {c_us_main}.
- **Crude oil context.** The rise in crude exports to other countries coincides with the expanded Trans Mountain pipeline, which started commercial service on May 1, 2024, before the US tariffs (Trans Mountain Corporation, a federal Crown corporation).

![Price and volume effects for gold and crude oil](figures/m4_price_volume.png)

### H3 · Did tariffed sectors sell less to the US without finding other buyers? **Confirmed for {h3_n_confirmed} of 5 sectors**

The rule, per sector: confirmed if the offset ratio is below {h3_lo}, rejected above {h3_hi}, partial in between. Each sector's window starts in the first full month after its first US tariff; softwood lumber has {lumber_months} months ({lumber_window}), compared with the same calendar months in the baseline.

{h3_table}

{h3_bullets}
- **Comparison: the fall in US sales is concentrated in the tariffed sectors.** Products with no sector-specific US tariff, without gold and energy, changed {grp_us}% to the US and {grp_row}% to other countries over the same months (with gold and energy: {grp_us_all}% and {grp_row_all}%). Their exports to the US rose, so no offset ratio is defined for them.
- **Sensitivity.** With the 2023–2024 baseline the verdicts are {h3_same} (comparison group: {grp_us_sens}% to the US, {grp_row_sens}% elsewhere).

![Offset ratio by tariffed sector and % changes next to the comparison group](figures/h3_redirection.png)

### H4 · Did new export pairs outside the US stay within the pre-tariff range? **{h4_header}**

The rule: confirmed if the count at the latest month is within ±{h4_band} of the baseline mean; rejected if above. The baseline mean uses the two frozen snapshots, December 2023 and December 2024, for both baselines.

- **{h4_edge}**
- In {h4_snapshot}, {h4_count} product–country pairs outside the US were new. The baseline mean is {h4_mean}, so the band is {h4_low}–{h4_high} (upper limit {h4_high_exact}). The count is {h4_change_abs}% above the mean. {h4_same}.
- Without gold, and without gold and energy, the pattern is the same:

{h4_table}

- **Front-loading pushes the count down.** The latest snapshot looks back at 12 months that include November 2024 to February 2025, when exports to non-US countries were {fl_nonus_abs}% higher than a year earlier. A higher starting point makes fewer pairs look new.
- **Context only, not verdicts.** *Exploratory, defined after seeing the result:* against the {h4_explo_ref} alone ({h4_explo_n} pairs), the latest count is {h4_explo_change}%. *Post hoc:* {h4_post_month}, the same calendar month as the baseline snapshots, had {h4_post_n} new pairs ({h4_post_change}% vs the baseline mean).

**Where the new pairs rose most.** Against each destination's own baseline mean, the largest rises are in {h4_risers}. {h4_risers_gold} By product, {h4_hs2_riser} rose most against its baseline, while {h4_hs2_leader} still has the most new pairs ({h4_top_hs2_share} of the total). {h4_top_country} has the most new pairs of any destination ({h4_top_country_n}, baseline mean {h4_top_country_mean}).

{h4_country_table}

{h4_chapter_table}

![New export pairs outside the US against the frozen band](figures/h4_new_pairs.png)

![Top destinations and HS2 chapters by new export pairs](figures/h4_where_new_pairs.png)

### Sector exposure · How dependent is each sector on the US?

Descriptive only, no hypothesis test. Ordered by US dependence in the latest 12 months; baseline 2022–2024. HHI (destination concentration) is 1 when a sector sells to one country only.

{m8_table}

- {m8_top_cap} still depend most on the US.
- The largest change is in {m8_drop}: from {m8_drop_base}% to {m8_drop_latest}% of its exports going to the US. It is a small sector (CAD {m8_drop_size} billion of exports in the latest 12 months).
- "Under a US sector tariff" is the share of the sector's latest exports covered fully or partly by a sector-specific US measure in the latest month (partial = only some tariff lines or part of the value, for example USMCA content).

![US dependence by sector, baseline vs latest 12 months](figures/m8_exposure.png)

## Limitations

- **Description, not cause.** The results show what changed alongside the tariffs. They do not prove the tariffs caused it.
- **Gold is volatile.** Gold exports depend on world gold prices and on where bullion is refined and stored, so the gold effect can swing from year to year.
- **Customs basis.** Canada's exports to the US are measured with US import data under a Canada–US data exchange. The customs US share and the balance-of-payments share differ by at most {v2_gap} points in the periods checked (validation check V2).
- **Front-loading.** Exports surged before the tariffs. Those months are left out, but some early shipping may fall outside the excluded window.
- **New pairs need time.** A pair counts as new only after three month-ends above CAD 1 million, so flows that started recently are not counted yet. The H4 count sits {h4_room} its upper limit, so small data revisions can change the verdict.
- **Comparison group still paid some duties.** Products with no sector-specific tariff that did not qualify for USMCA still paid across-the-board US duties (IEEPA, March 2025 to February 2026, then Section 122 and Section 301).
- **Lumber and US tariffs in general.** Softwood lumber already paid US anti-dumping and countervailing duties before 2025, and across-the-board US tariffs applied to goods that did not qualify for USMCA. More detail: [docs/methodology.md](docs/methodology.md#limitations).

## How to reproduce

```bash
make setup   # Python 3.14 virtual environment and pinned packages
make all     # download → validate → build marts → figures → notebooks → reports → CSV
make test    # unit tests
```

Raw downloads are listed with checksums in [data/raw/MANIFEST.csv](data/raw/MANIFEST.csv). Notebooks: [01 H1](notebooks/01_h1_decomposition.ipynb), [02 H2](notebooks/02_h2_gold_energy_waterfall.ipynb), [03 H3](notebooks/03_h3_redirection.ipynb), [04 H4](notebooks/04_h4_extensive_margin.ipynb), [05 sector exposure](notebooks/05_sector_exposure.ipynb). Analyst pack (Excel): [excel/analyst_pack.xlsx](excel/analyst_pack.xlsx).

## Sources

Every source, with its tier, URL and access date: [docs/sources.md](docs/sources.md).

## License

- **Code:** MIT License, see [LICENSE](LICENSE).
- **Data:** Statistics Canada data are used under the [Open Government Licence – Canada](https://open.canada.ca/en/open-government-licence-canada) (version 2.0). Source: Statistics Canada. The CSV files in `data/processed/csv/` are derived from these data. Other sources keep their own terms, listed in [docs/sources.md](docs/sources.md).
