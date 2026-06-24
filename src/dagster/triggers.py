import datetime

import dagster as dg

from .constants import StockPriceConfig
from .jobs import job_ingest_daily_stock_prices


@dg.schedule(
    cron_schedule="0 9 * * 2-6",
    job=job_ingest_daily_stock_prices,
    execution_timezone="Asia/Singapore",
    default_status=dg.DefaultScheduleStatus.STOPPED,
    description="Hourly schedule during AU working hours to ingest trade book and refresh portfolio results, but only if the AU Daily refresh is not running"
)
def au_schedule_ingest_trade_book_and_refresh_portfolio_results(context: dg.ScheduleEvaluationContext):
    return dg.RunRequest(
        run_key=datetime.datetime.now().strftime("%Y-%m-%d-%H-%M"),
        run_config={
            "get_stock_open_close_prices_long_format": StockPriceConfig(
                start=(datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
                end=datetime.datetime.now().strftime("%Y-%m-%d")
            )
        }
    )
