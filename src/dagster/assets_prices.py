from datetime import datetime, UTC

import dagster as dg
from dagster_aws.s3 import S3Resource
import pandas as pd

from .constants import StockPriceConfig
from .s3_utils import (
    create_s3_date_directory,
    upload_parquet_to_s3
)
from ..portfolio_tracker.market_data import MarketDataClient


@dg.asset(
    description="Fetches stock open and close prices from Yahoo Finance and uploads the data to S3 in Parquet format.",
    group_name="market_data",
    kinds={"python"},
)
def stock_open_close_prices(
    context: dg.AssetExecutionContext,
    config: StockPriceConfig
) -> dg.MaterializeResult:
    context.log.info(f"Fetching stock open and close prices for tickers: {config.tickers}")
    market_data_client = MarketDataClient()
    df_stock_prices = market_data_client.get_stock_open_close_prices_long_format(
        tickers=config.tickers,
        period=config.period,
        interval=config.interval,
        auto_adjust=config.auto_adjust
    )
    context.add_output_metadata(
        metadata={
            "tickers": config.tickers,
            "rows": len(df_stock_prices),
            "preview": dg.MetadataValue.md(df_stock_prices.head().to_markdown(index=False)),
        }
    )
    return df_stock_prices


@dg.asset(
    description="Uploads stock open and close prices to S3 in Parquet format.",
    group_name="market_data",
    kinds={"s3"},
)
def s3_stock_open_close_prices(
    context: dg.AssetExecutionContext,
    config: StockPriceConfig,
    s3: S3Resource,
    stock_open_close_prices: pd.DataFrame
) -> dg.MaterializeResult:
    epoch_time = int(datetime.now(UTC).timestamp())
    key = f"{config.s3_prefix}/{create_s3_date_directory()}/{epoch_time}.parquet"

    upload_parquet_to_s3(
        s3=s3,
        df=stock_open_close_prices,
        bucket=config.s3_bucket,
        key=key,
        index=False,
    )
    context.log.info(f"Wrote {len(stock_open_close_prices)} rows to s3://{config.s3_bucket}/{key}")
