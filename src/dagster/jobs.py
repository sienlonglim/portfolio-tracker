from dagster import (
    define_asset_job,
    AssetSelection,
    load_assets_from_modules
)

from . import (
    assets_prices
)


assets = load_assets_from_modules([assets_prices])

job_ingest_daily_stock_prices = define_asset_job(
    name="job_ingest_daily_stock_prices",
    selection=AssetSelection.assets(*assets)
)

jobs = [
    job_ingest_daily_stock_prices
]
