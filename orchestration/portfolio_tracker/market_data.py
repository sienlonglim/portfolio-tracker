from __future__ import annotations

import datetime
import logging
import os
import time
from typing import (
    Any,
    ClassVar,
    Iterable,
)

import pandas as pd
import requests
import yfinance as yf
from eodhd import APIClient
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class MarketDataClient(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    logger: logging.Logger = logging.getLogger(__name__)
    tickers: list[str] = Field(default_factory=list)
    _eodhd_api_key: str = os.getenv("EODHD_API_KEY")

    SEC_TICKERS_URL: ClassVar[str] = (
        "https://www.sec.gov/files/company_tickers_exchange.json"
    )
    USER_AGENT: ClassVar[str] = "example@gmail.com"
    REQUEST_SLEEP_SECONDS: ClassVar[int] = 2

    def _screen_for_non_us_tickers(
        self, tickers: Iterable[str] | None = None
    ) -> set[str]:
        """
        Screens for non-US tickers based on the presence of a dot in the ticker symbol.
        Args:
            tickers (Iterable[str]): List of stock tickers to screen.
        Returns:
            set[str]: A set of non-US tickers.
        """
        if not tickers:
            return set()
        return set([ticker for ticker in tickers if ".AS" in ticker])

    def _call_and_parse_yfinance_prices(
        self,
        tickers: Iterable[str],
        start: str | None = None,
        end: str | None = None,
        period: str | None = None,
        interval: str = "1d",
        auto_adjust: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Fetches stock prices from Yahoo Finance for the specified tickers and parameters.
        Args:
            tickers (Iterable[str]): List of stock tickers to fetch.
            start (str): Start date for historical data in 'YYYY-MM-DD' format. Overrides period if provided.
            end (str): End date for historical data in 'YYYY-MM-DD' format. Defaults to today if not provided.
            period (str): Lookback period for historical data (e.g., '1d', '5d', '1mo', '3mo', '1y').
            interval (str): Sampling interval for the data (e.g., '1d', '1h', '15m').
            auto_adjust (bool): Whether to return split/dividend-adjusted prices.
        Returns:
            list[dict[str, Any]]: A list of dictionaries containing stock prices in long format with columns:
            ticker, date, open, high, low, close, volume
        """
        if not tickers:
            return []
        self.logger.info(
            f"Fetching stock prices for tickers: {tickers} with params "
            f"start={start}, end={end}, period={period}, interval={interval}."
        )
        df = yf.download(
            tickers=tickers,
            period=period,
            start=start,
            end=end,
            interval=interval,
            auto_adjust=auto_adjust,
            group_by="ticker",
        )
        all_rows = []
        for ticker in tickers:
            df_temp = df[ticker].reset_index().dropna(how="any")
            df_temp.insert(0, "ticker", ticker)
            df_temp.columns = [col.lower() for col in df_temp.columns]
            all_rows.extend(df_temp.to_dict(orient="records"))
        return all_rows

    def _call_and_parse_eodhd_prices(
        self,
        tickers: Iterable[str] | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        period: str = "d",
    ) -> list[dict[str, Any]]:
        """
        Fetches stock prices from EOD Historical Data for the specified tickers and parameters.
        Args:
            tickers (Iterable[str]): List of stock tickers to fetch.
            from_date (str): Start date for historical data in 'YYYY-MM-DD' format.
            to_date (str): End date for historical data in 'YYYY-MM-DD' format.
            period (str): Sampling interval for the data (e.g., 'd', 'w', 'm').
        Returns:
            list[dict[str, Any]]: A list of dictionaries containing stock prices in long format with columns:
            ticker, date, open, high, low, close, volume
        """
        if not tickers:
            return []
        eodhd_client = APIClient(self._eodhd_api_key)
        all_rows = []
        self.logger.info(
            f"Fetching stock prices for tickers: {tickers} with params "
            f"from_date={from_date}, to_date={to_date}, period={period}."
        )
        for ticker in tickers:
            resp = eodhd_client.get_eod_historical_stock_market_data(
                symbol=ticker,
                period=period,
                from_date=from_date,
                to_date=to_date,
                order="a",
            )
            df_temp = pd.DataFrame(resp)
            df_temp.insert(0, "ticker", ticker)
            df_temp["close"] = df_temp["adjusted_close"]
            df_temp.drop(columns=["adjusted_close"], inplace=True)
            all_rows.extend(df_temp.to_dict(orient="records"))
        return all_rows

    def get_stock_open_close_prices_long_format(
        self,
        tickers: Iterable[str] | None = None,
        period: str | None = None,
        start: str | None = None,
        end: str | None = None,
        interval: str = "1d",
        auto_adjust: bool = True,
    ) -> pd.DataFrame:
        """
        Fetches stock open and close prices from Yahoo Finance for the specified tickers.
        Args:
            tickers (Iterable[str]): List of stock tickers to fetch. If None, fetches all configured tickers.
            period (str): Lookback period for historical data (e.g., '1d', '5d', '1mo', '3mo', '1y').
            start (str): Start date for historical data in 'YYYY-MM-DD' format. Overrides period if provided.
            end (str): End date for historical data in 'YYYY-MM-DD' format. Defaults to today if not provided.
            interval (str): Sampling interval for the data (e.g., '1d', '1h', '15m').
            auto_adjust (bool): Whether to return split/dividend-adjusted prices.
        Returns:
            pd.DataFrame: A DataFrame in long format with columns: ticker, date, open, close.
        """
        tickers = self.tickers or tickers
        non_us_tickers = self._screen_for_non_us_tickers(tickers)
        yfinance_tickers = set(tickers).difference(non_us_tickers)
        all_rows = []
        all_rows.extend(
            self._call_and_parse_yfinance_prices(
                tickers=yfinance_tickers,
                start=start,
                end=end,
                period=period,
                interval=interval,
                auto_adjust=auto_adjust,
            )
        )
        all_rows.extend(
            self._call_and_parse_eodhd_prices(
                tickers=non_us_tickers,
                from_date=start,
                to_date=end,
            )
        )
        # Concatenate all rows from yf and eodhd into a single DataFrame
        result = pd.DataFrame(all_rows)
        if not result.empty:
            result["date"] = pd.to_datetime(result["date"]).dt.date
        return result

    def _get_sec_ticker_universe(self, full: bool = False) -> pd.DataFrame:
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
            self.logger.info(
                f"Filtering SEC tickers to only include {len(self.tickers)} tickers."
            )
            return df[df["ticker"].isin(self.tickers)].copy()
        return df

    @staticmethod
    def classify_market_cap(market_cap: float | None) -> str | None:
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
        self, tickers: Iterable[str], as_dataframe: bool = True
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

    def build_ticker_information(self, batch_size: int = 100) -> pd.DataFrame:
        sec_ticker_universe = self._get_sec_ticker_universe()

        tickers = sec_ticker_universe["ticker"].tolist()
        yfinance_company_info = []
        for i in range(0, len(tickers), batch_size):
            batch = tickers[i : i + batch_size]
            info = self._get_yfinance_company_info(batch, as_dataframe=True)
            yfinance_company_info.append(info)
            time.sleep(self.REQUEST_SLEEP_SECONDS)

        df_yfinance_company_info = pd.concat(yfinance_company_info, ignore_index=True)
        df = sec_ticker_universe.merge(
            df_yfinance_company_info, on="ticker", how="left"
        )
        df["market_cap_class"] = df["market_cap"].apply(
            MarketDataClient.classify_market_cap
        )
        df["as_of_date"] = pd.Timestamp(datetime.datetime.now().date())
        return df
