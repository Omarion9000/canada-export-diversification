# Canada's exports after the 2025 US tariffs: gold accounts for {gold_share} of the drop in the US share

Omar Serrano · Data Analyst · [GitHub] · [LinkedIn]

**Data:** Statistics Canada, CIMT domestic exports (customs basis), {first_month}–{last_month}. Baseline 2022–2024 vs the latest 12 months ({tariff_start}–{tariff_end}). Thresholds frozen before the analysis.

## Key findings

1. **The US share changed {d_total_s} pp, from {s_base}% to {s_latest}%:** gold {d_gold_s} pp ({gold_share} of the drop), energy {d_energy_s} pp, everything else {d_rest_s} pp ({rest_share}). Shares may not sum to 100% due to rounding.
2. **Gold is mostly {g_row_main}, crude mostly {c_row_main}.** {g_row_price_share} of the CAD {g_row_dv} bn rise in gold exports to other countries is price; gold grams to the US {g_us_q}%. Crude to other countries {c_row_dir} CAD {c_row_dv} bn, {c_row_vol_share} volume, coinciding with the Trans Mountain expansion (in service May 1, 2024, before the tariffs).
3. **H2 {h2_verdict_cap}.** Without gold and energy the drop is {h2_ratio} of the headline (threshold {h2_limit}); {h2_ratio_sens} with the 2023–2024 baseline ({h2_verdict_sens}{thin_note}).
4. **H1 {h1_verdict_cap}.** About {h1_row_share} of the change is on the rest-of-world side (exports elsewhere {row_growth}%, to the US {us_growth}%); {h1_row_share_x} without gold and energy, where the US share still fell {d_rest} points.
5. **H3: {h3_rejected} redirected; {h3_confirmed} did not.** Offset ratio {alu_or} for {h3_rejected} ({alu_cents} cents gained elsewhere per US dollar lost); below {h3_lo} for {h3_confirmed}; {h3_partial} partial. Products with no sector-specific tariff: {grp_us}% to the US, so the fall in US sales is concentrated in the tariffed sectors.
6. **H4.** {h4_edge} Largest rises vs the baseline: {h4_risers_short}. HS {h4_top_hs2} {h4_top_hs2_short} has the most ({h4_top_hs2_n}).
7. **Exposure.** {m8_top_cap} depend most on the US; {m8_drop} (CAD {m8_drop_size} bn a year) fell from {m8_drop_base}% to {m8_drop_latest}%.

<img src="../figures/h2_waterfall.png" alt="Waterfall of the change in the US share" width="75%">

**How to read this.** Most of the drop is linked to exports elsewhere growing, and gold is {gold_row_growth_share} of that growth. Outside gold, the clearest shifts are in {h3_rejected} and in new {h4_top_hs2_short} pairs. Associations, not proof of cause. **Method:** 12-month sums; front-loading months (Nov 2024–Feb 2025) left out; gold and energy effects average two removal orders (gold {gold_lo_s} to {gold_hi_s} pp); validated against Statistics Canada tables (data of {vintage}).
