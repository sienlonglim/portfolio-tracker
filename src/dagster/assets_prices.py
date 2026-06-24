from datetime import datetime, UTC

import dagster as dg
from dagster_aws.s3 import S3Resource
import pandas as pd

from .constants import StockPriceConfig
from .s3_utils import (
    create_s3_date_directory,
    upload_parquet_to_s3
)
from .resources import MotherDuckS3Resource
from ..portfolio_tracker.market_data import MarketDataClient


@dg.asset(
    description="Fetches stock open and close prices from Yahoo Finance and uploads the data to S3 in Parquet format.",
    group_name="market_data",
    kinds={"python", "motherduck"},
)
def stock_open_close_prices(
    context: dg.AssetExecutionContext,
    config: StockPriceConfig,
    motherduck: MotherDuckS3Resource,
) -> dg.MaterializeResult:
    if not config.tickers:
        tickers = motherduck.query(
            database=config.motherduck_database,
            sql="select distinct sym as ticker from seed.seed_portfolio_positions",
            as_dataframe=True
        )["ticker"].tolist()
    else:
        tickers = config.tickers
    context.log.info(f"Fetching stock open and close prices for tickers: {tickers}")
    market_data_client = MarketDataClient(logger=context.log, tickers=tickers)
    if config.start and config.end:
        df_stock_prices = market_data_client.get_stock_open_close_prices_long_format(
            start=config.start,
            end=config.end,
            interval=config.interval,
            auto_adjust=config.auto_adjust
        )
    else:
        df_stock_prices = market_data_client.get_stock_open_close_prices_long_format(
            period=config.period,
            interval=config.interval,
            auto_adjust=config.auto_adjust
        )
    context.add_output_metadata(
        metadata={
            "tickers": tickers,
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


@dg.asset(
    description="Copies stock open and close prices from S3 into a MotherDuck table.",
    group_name="market_data",
    kinds={"s3", "motherduck"},
    deps=["s3_stock_open_close_prices"]
)
def copy_into_duckdb(
    context: dg.AssetExecutionContext,
    config: StockPriceConfig,
    motherduck: MotherDuckS3Resource,
) -> None:
    context.log.info(
        f"Copying data into MotherDuck database '{config.motherduck_database}', "
        f"table '{config.motherduck_schema}.{config.motherduck_table}'"
    )
    motherduck.copy_into_duckdb(
        s3_path=f"s3://{config.s3_bucket}/{config.s3_prefix}",
        database=config.motherduck_database,
        table_name=config.motherduck_table,
        schema=config.motherduck_schema,
        file_format="parquet",
        scope=None,
        full_refresh=config.full_refresh,
    )
    context.log.info("Success")
