# Canada's exports after the 2025 US tariffs: gold accounts for {gold_share} of the drop in the US share

Omar Serrano · Data Analyst · [GitHub] · [LinkedIn]

**Data:** Statistics Canada, CIMT domestic exports (customs basis), {first_month}–{last_month}. Baseline 2022–2024 vs the latest 12 months ({tariff_start}–{tariff_end}).

## Key findings

1. **The US share changed {d_total_s} pp, from {s_base}% to {s_latest}%.**
2. **Gold {d_gold_s} pp ({gold_share} of the drop),** energy {d_energy_s} pp on average, everything else {d_rest_s} pp ({rest_share}). Shares may not sum to 100% due to rounding.
3. **Gold: mostly {g_row_main}.** {g_row_price_share} of the CAD {g_row_dv} bn rise in gold exports to other countries is a price effect; the volume of gold to the US fell (volume effect CAD {g_us_ve_s} bn, grams {g_us_q}%).
4. **Crude: mostly {c_row_main}.** Crude oil exports to other countries {c_row_dir} by CAD {c_row_dv} bn a year; {c_row_vol_share} of that is a volume effect (CAD {c_row_ve_s} bn). This coincides with the expanded Trans Mountain pipeline starting service on May 1, 2024, before the tariffs.
5. **H2 {h2_verdict_cap}.** Without gold and energy, the drop is {h2_ratio} of the headline (frozen threshold: at most {h2_limit}). With the 2023–2024 baseline it is {h2_ratio_sens} against the {h2_limit} threshold ({h2_verdict_sens}{thin_note}).
6. **H1 {h1_verdict_cap}.** About {h1_row_share} of the change is linked to faster growth in exports to other countries (CAD {x_row_base} bn → {x_row_latest} bn a year, {row_growth}%). Exports to the US changed {us_growth}% (CAD {x_us_base} bn → {x_us_latest} bn). Without gold and energy: {h1_row_share_x} on the rest-of-world side ({h1_verdict_x}).

![Waterfall of the change in the US share](../figures/h2_waterfall.png)

## How to read this

- The US share can fall because exports to the US shrink or because exports elsewhere grow. Here it is mostly the second. Gold accounts for {gold_row_growth_share} of the growth in exports to other countries (CAD {gold_row_change_bn} bn of {row_change_bn} bn).
- Without gold and energy, the US share still fell {d_rest} points, mostly on the rest-of-world side: exports to other countries changed {row_growth_x}%.
- These are associations, not proof that the tariffs caused the change.

## Method in one paragraph

Shares use 12-month sums. The baseline averages each calendar month over 2022–2024 and leaves out the front-loading months (November 2024–February 2025). Gold (HS 7108) and energy (HS 27) effects are the average of two removal orders; the gold effect ranges from {gold_lo_s} to {gold_hi_s} pp between orders. Thresholds were frozen before the analysis. All checks against published Statistics Canada tables passed (data downloaded {vintage}).

**Next:** product-level redirection in tariffed sectors (H3), new product–market pairs (H4) and a sector exposure table.
