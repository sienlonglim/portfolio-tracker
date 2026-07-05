from datetime import UTC, datetime

import dagster as dg

from .constants import PositionsConfig
from .resources import MotherDuckS3Resource


@dg.asset(
    description="Backup raw table into S3 in Parquet format.",
    group_name="positions",
    kinds={"s3", "motherduck"},
)
def s3_positions_backup(
    context: dg.AssetExecutionContext,
    config: PositionsConfig,
    motherduck: MotherDuckS3Resource,
) -> None:
    context.log.info(
        f"Creating backup data into S3 from '{config.motherduck_database}', "
        f"table '{config.motherduck_schema}.{config.motherduck_table}'"
    )
    epoch_time = int(datetime.now(UTC).timestamp())
    motherduck.copy_into_s3(
        s3_path=f"s3://{config.s3_bucket}/{config.s3_prefix}",
        database=config.motherduck_database,
        table_name=config.motherduck_table,
        schema=config.motherduck_schema,
        filename=f"{epoch_time}.parquet",
    )
    context.log.info(f"Created backup data '{epoch_time}.parquet' into S3.")
