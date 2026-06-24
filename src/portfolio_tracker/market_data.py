from __future__ import annotations
import datetime
import requests
import logging
import time
from typing import (
    ClassVar,
    Optional
)

import pandas as pd
from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
)
import yfinance as yf


class MarketDataClient(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    logger: logging.Logger = logging.getLogger(__name__)
    tickers: list[str] = Field(default_factory=list)

    SEC_TICKERS_URL: ClassVar[str] = "https://www.sec.gov/files/company_tickers_exchange.json"
    USER_AGENT: ClassVar[str] = "example@gmail.com"
    REQUEST_SLEEP_SECONDS: ClassVar[int] = 2

    def get_stock_open_close_prices_long_format(
        self,
        tickers: list[str] | None = None,
        period: str = "1mo",
        start: Optional[str] = None,
        end: Optional[str] = None,
        interval: str = "1d",
        auto_adjust: bool = True
    ) -> pd.DataFrame:
        """
        Fetches stock open and close prices from Yahoo Finance for the specified tickers.
        Args:
            tickers (list[str]): List of stock tickers to fetch. If None, fetches all configured tickers.
            period (str): Lookback period for historical data (e.g., '1d', '5d', '1mo', '3mo', '1y').
            start (str): Start date for historical data in 'YYYY-MM-DD' format. Overrides period if provided.
            end (str): End date for historical data in 'YYYY-MM-DD' format. Defaults to today if not provided.
            interval (str): Sampling interval for the data (e.g., '1d', '1h', '15m').
            auto_adjust (bool): Whether to return split/dividend-adjusted prices.
        Returns:
            pd.DataFrame: A DataFrame in long format with columns: ticker, date, open, close.
        """
        if not tickers:
            tickers = self.tickers
        if start and end:
            self.logger.info(f"Fetching stock prices for tickers: {tickers} from {start} to {end} with interval {interval}.")
            df = yf.download(
                tickers=tickers,
                start=start,
                end=end,
                interval=interval,
                auto_adjust=auto_adjust,
                group_by='ticker',
            )
        else:
            self.logger.info(f"Fetching stock prices for tickers: {tickers} for period {period} with interval {interval}.")
            df = yf.download(
                tickers=tickers,
                period=period,
                interval=interval,
                auto_adjust=auto_adjust,
                group_by='ticker',
            )
        all_rows = []
        for ticker in tickers:
            df_temp = df[ticker].reset_index()
            df_temp.insert(0, 'ticker', ticker)
            df_temp.columns = [col.lower() for col in df_temp.columns]
            all_rows.extend(df_temp.to_dict(orient='records'))

        result = pd.DataFrame(all_rows)
        result["date"] = pd.to_datetime(result["date"]).dt.date
        return result

    def _get_sec_ticker_universe(
        self,
        full: bool = False
    ) -> pd.DataFrame:
        """
        Fetches the list of tickers from the SEC's company tickers exchange JSON.
        Args:
            full (bool): Whether to fetch the full dataset or a subset.
        Returns:
            pd.DataFrame: A DataFrame containing the SEC tickers, cik, company name, and exchange information.
        """
        headers = {"User-Agent": self.USER_AGENT, "Accept-Encoding": "gzip, deflate"}
        r = requests.get(self.SEC_TICKERS_URL, headers=headers, timeout=30)
        r.raise_for_status()
        payload = r.json()

        data, cols = payload.get("data", []), payload.get("fields", [])
        df = pd.DataFrame(data, columns=cols)
        if not full:
            self.logger.info(f"Filtering SEC tickers to only include {len(self.tickers)} tickers.")
            return df[df["ticker"].isin(self.tickers)].copy()
        return df

    @staticmethod
    def classify_market_cap(market_cap: Optional[float]) -> Optional[str]:
        if market_cap is None or pd.isna(market_cap):
            return None
        if market_cap >= 200_000_000_000:
            return "mega"
        if market_cap >= 10_000_000_000:
            return "large"
        if market_cap >= 2_000_000_000:
            return "mid"
        if market_cap >= 250_000_000:
            return "small"
        return "micro"

    def _get_yfinance_company_info(
        self,
        tickers: list[str],
        as_dataframe: bool = True
    ) -> pd.DataFrame:
        """
        Use yfinance in batch mode where possible.
        Fast enough for practical use, though not perfect.
        """
        if not tickers:
            tickers = self.tickers
        rows = []
        yt = yf.Tickers(" ".join(tickers))

        for ticker in tickers:
            self.logger.info(f"Fetching yfinance info for {ticker}")
            obj = yt.tickers[ticker]
            fast_info = getattr(obj, "fast_info", None)
            if fast_info:
                market_cap = fast_info.get("market_cap", None)
            if market_cap is None:
                market_cap = obj.info.get("marketCap")
            sector = obj.info.get("sector")
            industry = obj.info.get("industry")
            rows.append(
                {
                    "ticker": ticker,
                    "sector": sector,
                    "industry": industry,
                    "market_cap": market_cap,
                }
            )
        if as_dataframe:
            return pd.DataFrame(rows)
        return rows

    def build_ticker_information(
        self,
        batch_size: int = 100
    ) -> pd.DataFrame:
        sec_ticker_universe = self._get_sec_ticker_universe()

        tickers = sec_ticker_universe["ticker"].tolist()
        yfinance_company_info = []
        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i + batch_size]
            info = self._get_yfinance_company_info(batch, as_dataframe=True)
            yfinance_company_info.append(info)
            time.sleep(self.REQUEST_SLEEP_SECONDS)

        df_yfinance_company_info = pd.concat(yfinance_company_info, ignore_index=True)
        df = sec_ticker_universe.merge(df_yfinance_company_info, on="ticker", how="left")
        df["market_cap_class"] = df["market_cap"].apply(MarketDataClient.classify_market_cap)
        df["as_of_date"] = pd.Timestamp(datetime.datetime.now().date())
        return df
