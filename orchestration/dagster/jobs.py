from dagster import (
    define_asset_job,
    AssetSelection,
    load_assets_from_modules
)

from . import (
    assets_prices,
    assets_dbt
)

job_ingest_daily_stock_prices = define_asset_job(
    name="job_ingest_daily_stock_prices",
    selection=AssetSelection.assets(*load_assets_from_modules([assets_prices]))
)

job_dbt_build = define_asset_job(
    name="job_dbt_build",
    selection=AssetSelection.assets(*load_assets_from_modules([assets_dbt]))
)

jobs = [
    job_ingest_daily_stock_prices,
    job_dbt_build,
]
