-- Reference tables: StatCan WDS tables, prices, FX, country codes, tariff events and lists.
-- Values from WDS are already converted to dollars (or index points) in landing.

create or replace table ref_wds_0011 as
select
    basis,
    principal_trading_partners as partner,
    ref_date::date as month,
    value::double as value_cad
from raw_wds_0011
where trade = 'Export' and seasonal_adjustment = 'Unadjusted';

create or replace table ref_wds_0182 as
select
    north_american_product_classification_system_napcs as napcs,
    principal_trading_partner_exports_by_country_of_destination as partner,
    ref_date::date as month,
    value::double as value_cad
from raw_wds_0182;

create or replace table ref_wds_0171 as
select
    trading_partner as partner,
    year(ref_date::date) as year,
    value::double as value_cad
from raw_wds_0171;

create or replace table ref_wds_0168 as
select
    basis,
    index as index_type,
    north_american_product_classification_system_napcs as napcs,
    ref_date::date as month,
    value::double as index_value
from raw_wds_0168;

-- Monthly prices in USD (World Bank Pink Sheet).
create or replace table prices as
select month::date as month, series, value::double as value
from raw_prices;

-- USD/CAD monthly average (Bank of Canada).
create or replace table fx as
select month::date as month, usdcad::double as usdcad
from raw_fx;

create or replace table ref_country_codes as
select iso2, iso3, name from raw_sccai;

create or replace table ref_eu_members as
select iso2, name from raw_eu_members;

-- Tariff events: every row must cite a source URL.
create or replace table tariff_events as
select
    event_id,
    event_date::date as event_date,
    hs_scope,
    sector_group,
    measure,
    legal_basis,
    try_cast(rate_pct as double) as rate_pct,
    usmca_treatment,
    notes,
    document,
    source_url,
    access_date::date as access_date
from raw_tariff_events;

create or replace table tariff_lists as
select
    list_id,
    event_id,
    effective_date::date as effective_date,
    series,
    series_mode,
    sector_group,
    value_basis,
    usmca_exempt::boolean as usmca_exempt,
    url
from raw_tariff_lists;

create or replace table tariff_list_codes as
select list_id, code, level::int as level from raw_tariff_list_codes;

create or replace table us_hts8 as
select hts8, hs6, hts_release from raw_us_hts8;
