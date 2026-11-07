# Canada Export Diversification Under US Tariffs

**Short answer.** Since the 2025 US tariffs, the US share of Canada's goods exports fell by {d_total} percentage points, from {s_base}% to {s_latest}%. Gold accounts for {gold_share} of that drop ({d_gold} points), and most of the rise in gold exports is a price effect, not more gold shipped. Without gold and energy, the share fell only {d_rest} points, and that smaller drop is linked mostly to growth in exports to other countries, not to a fall in exports to the US.

![Waterfall of the change in the US share of Canada's exports](figures/h2_waterfall.png)

*Baseline 2022–2024 vs the latest 12 months ({tariff_start}–{tariff_end}). Gold and energy effects are the average of two removal orders.*

> Status: first results (H1 and H2). The product-level tests (H3, H4) and the sector exposure table come next.

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

## Limitations

- **Description, not cause.** The results show what changed alongside the tariffs. They do not prove the tariffs caused it.
- **Gold is volatile.** Gold exports depend on world gold prices and on where bullion is refined and stored, so the gold effect can swing from year to year.
- **Customs basis.** Canada's exports to the US are measured with US import data under a Canada–US data exchange. The customs US share and the balance-of-payments share differ by at most {v2_gap} points in the periods checked (validation check V2).
- **Front-loading.** Exports surged before the tariffs. Those months are left out, but some early shipping may fall outside the excluded window.
- **Lumber and US tariffs in general.** Softwood lumber already paid US anti-dumping and countervailing duties before 2025, and across-the-board US tariffs applied to goods that did not qualify for USMCA. More detail: [docs/methodology.md](docs/methodology.md#limitations).

## How to reproduce

```bash
make setup   # Python 3.14 virtual environment and pinned packages
make all     # download → validate → build marts → figures → notebooks → reports → CSV
make test    # unit tests
```

Raw downloads are listed with checksums in [data/raw/MANIFEST.csv](data/raw/MANIFEST.csv). Notebooks: [01 H1](notebooks/01_h1_decomposition.ipynb), [02 H2](notebooks/02_h2_gold_energy_waterfall.ipynb).

## Sources

Every source, with its tier, URL and access date: [docs/sources.md](docs/sources.md).
