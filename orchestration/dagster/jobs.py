from dagster import AssetSelection, define_asset_job, load_assets_from_modules

from . import assets_dbt

job_ingest_daily_stock_prices = define_asset_job(
    name="job_ingest_daily_stock_prices",
    selection=AssetSelection.groups("market_data")
)

job_dbt_build = define_asset_job(
    name="job_dbt_build",
    selection=AssetSelection.assets(*load_assets_from_modules([assets_dbt])),
)

job_backup_positions = define_asset_job(
    name="job_backup_positions",
    selection=AssetSelection.groups("positions")
)

jobs = [
    job_ingest_daily_stock_prices,
    job_dbt_build,
    job_backup_positions,
]
