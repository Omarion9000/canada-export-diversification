"""V1a, V1b, V2, V3, V4, V5, V6 checks.

Each check returns a CheckResult. Halting checks that fail stop the pipeline after the
report is written (see src/validate/__main__.py).
"""

from dataclasses import dataclass, field

import duckdb
import pandas as pd

from src.common import CONFIG, load_settings

TROY_OUNCE_GRAMS = 31.1034768  # exact by definition


@dataclass
class CheckResult:
    check_id: str
    title: str
    status: str  # PASS | FAIL | FLAG | LOG
    halting: bool
    summary: str
    details: pd.DataFrame = field(default_factory=pd.DataFrame)
    note: str = ""


def df(con: duckdb.DuckDBPyConnection, sql: str) -> pd.DataFrame:
    return con.execute(sql).df()


def register_crosswalk(con) -> None:
    """StatCan table partner name -> CIMT country code, for names that differ."""
    path = CONFIG / "statcan_partner_crosswalk.csv"
    con.register("crosswalk_df", pd.read_csv(path, dtype=str))


def v1a(con) -> CheckResult:
    tol = load_settings()["thresholds"]["v1_tolerance_pct"]
    register_crosswalk(con)
    details = df(con, """
        with names as (
            select code as country_code, name
            from raw_country_desc
            qualify row_number() over (partition by code order by end_yyyymm desc) = 1
        ),
        statcan as (
            select r.year, r.partner,
                   coalesce(x.country_code, n.country_code,
                            case when r.partner = 'All countries' then 'ALL' end) as country_code,
                   r.value_cad as statcan_value
            from ref_wds_0171 r
            left join crosswalk_df x on x.statcan_name = r.partner
            left join names n on n.name = r.partner
            where r.year >= year(p('first_month')::date)
        ),
        cimt as (
            select year(month) as year, country_code, sum(value_cad) as cimt_value
            from ref_cimt_total_exports group by all
            union all
            select year(month), 'ALL', sum(value_cad) from ref_cimt_total_exports group by all
        ),
        full_years as (
            select year(month) as year from ref_cimt_total_exports
            group by 1 having count(distinct month) = 12
        )
        select s.year, s.partner, s.country_code, s.statcan_value,
               coalesce(c.cimt_value, 0) as cimt_value,
               coalesce(c.cimt_value, 0) - s.statcan_value as diff,
               case when s.statcan_value > 0
                    then 100 * (coalesce(c.cimt_value, 0) - s.statcan_value) / s.statcan_value
               end as diff_pct
        from statcan s
        join full_years using (year)
        left join cimt c on c.year = s.year and c.country_code = s.country_code
        where s.statcan_value > 0 or coalesce(c.cimt_value, 0) > 0
        order by s.year, s.statcan_value desc
    """)
    # The relative test applies to country-years of at least CAD 1 million.
    tested = details[details["statcan_value"] >= 1e6]
    fails = tested[tested["diff_pct"].abs() > tol]
    unmapped = details[details["country_code"].isna()]
    status = "PASS" if fails.empty and unmapped.empty else "FAIL"
    total = details[details["country_code"] == "ALL"]
    summary = (
        f"{len(tested)} country-years >= CAD 1M tested, {len(fails)} outside ±{tol}%; "
        f"{len(unmapped)} partner names unmapped. All-countries gap by year: "
        + ", ".join(f"{int(r.year)}: {r.diff_pct:+.3f}%" for r in total.itertuples())
    )
    out = pd.concat([total, fails, unmapped]).drop_duplicates()
    return CheckResult("V1a", "Annual total exports by country, CIMT vs StatCan 12-10-0171-01",
                       status, True, summary, out,
                       "Independent StatCan publication (annual, customs basis, total exports).")


def v1b(con) -> CheckResult:
    tol = load_settings()["thresholds"]["v1_tolerance_pct"]
    register_crosswalk(con)
    details = df(con, """
        with names as (
            select code as country_code, name
            from raw_country_desc
            qualify row_number() over (partition by code order by end_yyyymm desc) = 1
        ),
        statcan as (
            select r.month, replace(r.partner, ', country of destination', '') as partner,
                   r.value_cad as statcan_value
            from ref_wds_0182 r
            where r.napcs = 'All sections' and r.month >= p('first_month')::date
        ),
        mapped as (
            select s.*,
                   case when s.partner = 'All countries' then 'ALL'
                        when s.partner = 'Other countries' then 'OTHER'
                        else coalesce(x.country_code, n.country_code) end as country_code
            from statcan s
            left join crosswalk_df x on x.statcan_name = s.partner
            left join names n on n.name = s.partner
        ),
        named as (select distinct country_code from mapped
                  where country_code not in ('ALL', 'OTHER')),
        cimt as (
            select month, country_code, sum(value_cad) as cimt_value
            from fact_exports where country_code in (select country_code from named) group by all
            union all
            select month, 'ALL', sum(value_cad) from fact_exports group by all
            union all
            select month, 'OTHER', sum(value_cad) from fact_exports
            where country_code not in (select country_code from named) group by all
        )
        select m.month, m.partner, m.country_code, m.statcan_value,
               coalesce(c.cimt_value, 0) as cimt_value,
               100 * (coalesce(c.cimt_value, 0) - m.statcan_value) / m.statcan_value as diff_pct
        from mapped m
        left join cimt c using (month, country_code)
        where m.month <= (select max(month) from fact_exports)
        order by m.month, m.statcan_value desc
    """)
    fails = details[(details["diff_pct"].abs() > tol) | details["country_code"].isna()]
    status = "PASS" if fails.empty else "FAIL"
    summary = (f"{len(details)} partner-months compared (28 partners + other + all), "
               f"{len(fails)} outside ±{tol}%. Max |gap| {details['diff_pct'].abs().max():.4f}%.")
    return CheckResult("V1b", "Monthly domestic exports by principal trading partner, "
                       "CIMT vs StatCan 12-10-0182-01", status, True, summary, fails,
                       "Consistency test only: both come from the same StatCan trade source, "
                       "so this is not an independent validation.")


def v1_eu(con) -> CheckResult:
    tol = load_settings()["thresholds"]["v1_tolerance_pct"]
    details = df(con, """
        with cimt as (
            select t.month, sum(t.value_cad) as cimt_value
            from ref_cimt_total_exports t
            join ref_eu_members e on e.iso2 = t.country_code
            group by 1
        )
        select r.month, r.value_cad as statcan_value, c.cimt_value,
               100 * (c.cimt_value - r.value_cad) / r.value_cad as diff_pct
        from ref_wds_0011 r join cimt c using (month)
        where r.basis = 'Customs' and r.partner = 'European Union'
        order by 1
    """)
    fails = details[details["diff_pct"].abs() > tol]
    status = "PASS" if fails.empty else "FAIL"
    summary = (f"{len(details)} months: CIMT total exports to the 27 EU members vs 12-10-0011-01 "
               f"'European Union' (customs). Max |gap| {details['diff_pct'].abs().max():.4f}%.")
    return CheckResult("V1-EU", "EU grouping check (27 members, UK excluded)", status, True,
                       summary, fails, "Confirms the EU member list in config/eu_members.csv.")


def v2(con) -> CheckResult:
    max_gap = load_settings()["thresholds"]["v2_max_gap_pp"]
    details = df(con, """
        with windows as (
            select distinct year(month)::varchar as window_id, year(month) as y,
                   min(month) over (partition by year(month)) as start_month,
                   max(month) over (partition by year(month)) as end_month
            from dim_month
            union all
            select 'latest 12 months', null, min(month), max(month)
            from dim_month where period_label = 'tariff'
        ),
        complete as (
            select * from windows where datediff('month', start_month, end_month) = 11
        ),
        cimt as (
            select w.window_id,
                   100 * sum(f.value_cad) filter (where f.country_code = 'US') / sum(f.value_cad)
                       as us_share_customs_domestic
            from complete w join fact_exports f on f.month between w.start_month and w.end_month
            group by 1
        ),
        bop as (
            select w.window_id,
                   100 * sum(r.value_cad) filter (where r.partner = 'United States')
                       / sum(r.value_cad) filter (where r.partner = 'All countries')
                       as us_share_bop
            from complete w join ref_wds_0011 r on r.month between w.start_month and w.end_month
            where r.basis = 'Balance of payments'
            group by 1
        )
        select c.window_id, c.us_share_customs_domestic, b.us_share_bop,
               c.us_share_customs_domestic - b.us_share_bop as gap_pp
        from cimt c join bop b using (window_id) order by 1
    """)
    worst = details["gap_pp"].abs().max()
    status = "PASS" if worst <= max_gap else "FAIL"
    summary = f"Largest |gap| {worst:.2f} pp (limit {max_gap} pp)."
    return CheckResult("V2", "US share: customs domestic exports (CIMT) vs BOP (12-10-0011-01)",
                       status, True, summary, details,
                       "BOP adjusts customs data for coverage, valuation and timing; small gaps "
                       "are expected.")


def v3(con) -> CheckResult:
    tol = load_settings()["thresholds"]["v3_tolerance_pct"]
    details = df(con, f"""
        with uv as (
            select month, sum(value_cad) / sum(quantity) as cad_per_gram
            from fact_exports where hs6 = '710812' and qty_unit = 'GRM' and quantity > 0
            group by 1
        )
        select u.month, u.cad_per_gram,
               pr.value * fx.usdcad / {TROY_OUNCE_GRAMS} as pink_sheet_cad_per_gram,
               100 * (u.cad_per_gram / (pr.value * fx.usdcad / {TROY_OUNCE_GRAMS}) - 1) as diff_pct
        from uv u
        join prices pr on pr.month = u.month and pr.series = 'gold_usd_per_troy_oz'
        join fx on fx.month = u.month
        order by 1
    """)
    flags = details[details["diff_pct"].abs() > tol]
    status = "PASS" if flags.empty else "FLAG"
    summary = (f"{len(details)} months, {len(flags)} outside ±{tol}%. Median gap "
               f"{details['diff_pct'].median():+.2f}%.")
    return CheckResult("V3", "Gold unit value (HS 7108.12) vs World Bank gold price in CAD",
                       status, False, summary, flags)


def v4(con) -> CheckResult:
    details = df(con, """
        with periods as (
            -- Full calendar years, plus year-to-date for the latest (partial) year.
            select year(month) as y, max(month(month)) as last_m from dim_month group by 1
        ),
        latest as (select max(y) as y, max_by(last_m, y) as m from periods),
        cimt as (
            select year(f.month) as y, 'total' as series, sum(f.value_cad) as v
            from fact_exports f, latest l where month(f.month) <= l.m group by 1
            union all
            select year(f.month), 'gold', sum(f.value_cad)
            from fact_exports f join dim_product d using (hs6), latest l
            where d.is_gold and month(f.month) <= l.m group by 1
        ),
        ref as (
            select year(month) as y, 'total' as series, sum(value_cad) as v
            from ref_wds_0011, latest l
            where basis = 'Customs' and partner = 'All countries' and month(month) <= l.m
              and month >= p('first_month')::date
            group by 1
            union all
            select year(month), 'gold', sum(value_cad)
            from ref_wds_0182, latest l
            where napcs like 'Unwrought gold%' and partner like 'All countries%'
              and month(month) <= l.m and month >= p('first_month')::date
            group by 1
        ),
        growth as (
            select c.series, c.y,
                   c.v / lag(c.v) over (partition by c.series order by c.y) - 1 as cimt_growth,
                   r.v / lag(r.v) over (partition by r.series order by r.y) - 1 as ref_growth
            from cimt c join ref r using (series, y)
        )
        select series, y as year, cimt_growth, ref_growth,
               sign(cimt_growth) = sign(ref_growth) as same_direction
        from growth where cimt_growth is not null order by 1, 2
    """)
    flags = details[~details["same_direction"]]
    status = "PASS" if flags.empty else "FLAG"
    summary = (f"{len(details)} year-over-year comparisons (same months each year), "
               f"{len(flags)} with opposite direction.")
    return CheckResult(
        "V4", "Direction of total and gold exports vs StatCan published tables", status, False,
        summary, details,
        "Uses the tables behind The Daily: 12-10-0011-01 (customs, all countries, total exports) "
        "for totals and 12-10-0182-01 'Unwrought gold, silver, and platinum group metals' for gold "
        "(the gold reference is from the same source, so it is a consistency test).")


def v5(con) -> CheckResult:
    queries = {
        "duplicate keys (month, country, HS6)":
            "select count(*) from (select month, country_code, hs6 from fact_exports "
            "group by all having count(*) > 1)",
        "negative values or quantities":
            "select count(*) from fact_exports where value_cad < 0 or quantity < 0",
        "missing months between first and latest":
            "select count(*) from dim_month m where not exists "
            "(select 1 from fact_exports f where f.month = m.month)",
        "months outside dim_month":
            "select count(*) from fact_exports f where not exists "
            "(select 1 from dim_month m where m.month = f.month)",
        "HS6 not valid for the month (StatCan HS6 description dates)":
            "select count(*) from (select distinct hs6, month from fact_exports) f "
            "where not exists (select 1 from raw_hs6_desc d where d.code = f.hs6 "
            "and strftime(f.month, '%Y%m') between d.start_yyyymm and d.end_yyyymm)",
        "HS6 not 6 digits":
            "select count(*) from dim_product where not regexp_full_match(hs6, '[0-9]{6}')",
        "countries without ISO3 or group":
            "select count(*) from dim_country where country_iso3 is null or ptp_group is null",
        "fact rows without country ISO3":
            "select count(*) from fact_exports where country_iso3 is null",
        "products without sector group":
            "select count(*) from dim_product where sector_group is null",
        "tariff events without source URL":
            "select count(*) from tariff_events where source_url is null or source_url = ''",
        "tariff period starts before the earliest allowed month":
            "select count(*) from (select min(month) as s from dim_month "
            "where period_label = 'tariff') where s < p('tariff_earliest_start')::date",
        "tariff period is not 12 months":
            "select count(*) from (select count(*) as n from dim_month "
            "where period_label = 'tariff') where n <> 12",
        "scope table not a full product x month grid":
            "select abs((select count(*) from staging_tariff_scope_monthly) - "
            "(select count(*) from dim_product) * (select count(*) from dim_month))",
        "mixed quantity units within one HS6 and month":
            "select count(*) from (select hs6, month from fact_exports "
            "group by all having count(distinct qty_unit) > 1)",
    }
    rows = [(name, con.execute(sql).fetchall()[0][0]) for name, sql in queries.items()]
    details = pd.DataFrame(rows, columns=["check", "exceptions"])
    bad = details[details["exceptions"] > 0]
    status = "PASS" if bad.empty else "FAIL"
    summary = f"{len(details)} integrity checks, {len(bad)} with exceptions."
    return CheckResult("V5", "Keys, signs, months, HS6 codes, country mapping", status, True,
                       summary, details)


def v6(con) -> CheckResult:
    threshold = load_settings()["thresholds"]["v6_log_change_pct"]
    previous = con.execute("select p('cimt_previous_vintage')").fetchall()[0][0]
    current = con.execute("select p('cimt_vintage')").fetchall()[0][0]
    if not previous:
        return CheckResult("V6", "Vintage diff vs previous snapshot", "LOG", False,
                           f"First snapshot ({current}); no previous vintage to compare.")
    details = df(con, f"""
        with cur as (select month, country_code, sum(value_cad) v from fact_exports group by all),
             prev as (select month, country_code, sum(value_cad) v from fact_exports_previous
                      group by all)
        select coalesce(c.month, p.month) as month,
               coalesce(c.country_code, p.country_code) as country_code,
               p.v as previous_value, c.v as current_value,
               100 * (c.v - p.v) / nullif(p.v, 0) as change_pct
        from cur c full join prev p using (month, country_code)
        where p.v is null or c.v is null or abs(c.v - p.v) > {threshold} / 100 * abs(p.v)
        order by 1, 2
    """)
    summary = (f"Current {current} vs previous {previous}: {len(details)} month-country cells "
               f"changed by more than {threshold}% (or appeared/disappeared).")
    return CheckResult("V6", "Vintage diff vs previous snapshot", "LOG", False, summary, details)


ALL_CHECKS = [v5, v1a, v1b, v1_eu, v2, v3, v4, v6]
