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
from .sql import render_sql
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
    # Default run behaviour: If no tickers are provided, fetch all tickers based on missing data in the MotherDuck table.
    if not config.tickers:
        if config.full_refresh:
            context.log.info("Full refresh requested, fetching all ticker positions with max historical data.")
            df_ticker_max_dates = motherduck.query(
                database=config.motherduck_database,
                sql=render_sql("get_all_ticker_positions.sql.j2"),
                as_dataframe=True
            )
        else:
            context.log.info("No ticker list passed, defaulting to fetching all tickers based on missing data in DB.")
            df_ticker_max_dates = motherduck.query(
                database=config.motherduck_database,
                sql=render_sql("get_ticker_max_dates.sql.j2"),
                as_dataframe=True
            )
        all_frames = []
        tickers = []
        market_data_client = MarketDataClient(logger=context.log)
        for row in df_ticker_max_dates.itertuples(index=False):
            row_tickers = list(row.tickers)
            tickers.extend(row_tickers)
            if pd.isna(row.max_date):
                custom_args = {"period": "max"}
            else:
                custom_args = {
                    "start": row.max_date.strftime("%Y-%m-%d"),
                    "end": datetime.now().strftime("%Y-%m-%d")
                }
            df_temp = market_data_client.get_stock_open_close_prices_long_format(
                tickers=row_tickers,
                interval=config.interval,
                auto_adjust=config.auto_adjust,
                **custom_args
            )  
            all_frames.append(df_temp)
        df_stock_prices = (
            pd.concat(all_frames, ignore_index=True)
            if all_frames
            else pd.DataFrame(columns=["ticker", "date", "open", "close"])
        )
    # Custom run behaviour: If tickers are provided, fetch data for those tickers based on the provided start/end dates or period.
    else:
        tickers = config.tickers
        market_data_client = MarketDataClient(logger=context.log, tickers=tickers)
        if config.start_date and config.end_date:
            custom_args = {
                "start": config.start_date,
                "end": config.end_date
            }
        elif config.period:
            custom_args = {"period": config.period}
        else:
            raise ValueError("Either start_date and end_date or period must be provided in the config.")
        context.log.info(f"Fetching stock prices for tickers: {tickers} with custom arguments: {custom_args}")
        df_stock_prices = market_data_client.get_stock_open_close_prices_long_format(
            interval=config.interval,
            auto_adjust=config.auto_adjust,
            **custom_args
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
