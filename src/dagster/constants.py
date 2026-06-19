from pathlib import Path

from dagster import Config
from pydantic import Field


DBT_PROJECT_DIR = Path(__file__).resolve().parents[2] / "dbt"


class StockPriceConfig(Config):
    tickers: list[str] | None = Field(
        default_factory=list,
        description="Optional list of stock tickers to fetch. If omitted, fetch all/default configured tickers.",
    )
    s3_bucket: str = Field(
        default="sl-python-projects",
        description="Target S3 bucket name to write the output dataset to.",
    )
    s3_prefix: str = Field(
        default="portfolio-tracker-market_data/stock_prices/open_close",
        description="S3 key prefix where output files will be stored.",
    )
    period: str = Field(
        default="5y",
        description="Yahoo Finance lookback period, e.g. 1d, 5d, 1mo, 3mo, 1y.",
    )
    interval: str = Field(
        default="1d",
        description="Sampling interval, e.g. 1d, 1h, 15m.",
    )
    auto_adjust: bool = Field(
        default=True,
        description="Whether to return split/dividend-adjusted prices.",
    )
