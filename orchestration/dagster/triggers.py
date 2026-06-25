import datetime

import dagster as dg

from .jobs import job_ingest_daily_stock_prices


@dg.schedule(
    cron_schedule="0 9 * * 2-6",
    job=job_ingest_daily_stock_prices,
    execution_timezone="Asia/Singapore",
    default_status=dg.DefaultScheduleStatus.STOPPED,
    description="Daily schedule to ingest stock prices. Runs at 9am SGT on weekdays (Tue-Sat)."
)
def schedule_ingest_daily_stock_prices(context: dg.ScheduleEvaluationContext):
    return dg.RunRequest(run_key=datetime.datetime.now().strftime("%Y-%m-%d-%H-%M"))
