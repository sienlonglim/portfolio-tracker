import pandas as pd
import yfinance as yf


class MarketDataClient():
    def get_stock_open_close_prices_long_format(
        self,
        tickers: list[str] | None = None,
        period: str = "1mo",
        interval: str = "1d",
        auto_adjust: bool = True
    ) -> pd.DataFrame:
        """
        Fetches stock open and close prices from Yahoo Finance for the specified tickers.
        Args:
            tickers (list[str]): List of stock tickers to fetch. If None, fetches all configured tickers.
            period (str): Lookback period for historical data (e.g., '1d', '5d', '1mo', '3mo', '1y').
            interval (str): Sampling interval for the data (e.g., '1d', '1h', '15m').
            auto_adjust (bool): Whether to return split/dividend-adjusted prices.
        Returns:
            pd.DataFrame: A DataFrame in long format with columns: ticker, date, open, close.
        """
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
