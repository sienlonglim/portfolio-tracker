from dagster import (
    Definitions,
    EnvVar,
    load_assets_from_modules
)
from dagster_dbt import DbtCliResource
from dagster_aws.s3 import S3Resource

from . import (
    assets_dbt,
    assets_prices
)
from .jobs import jobs
from .constants import DBT_PROJECT_DIR


defs = Definitions(
    assets=load_assets_from_modules(modules=[assets_dbt, assets_prices]),
    jobs=jobs,
    resources={
        # "dbt": DbtCliResource(project_dir=str(DBT_PROJECT_DIR)),
        "s3": S3Resource(
            aws_access_key_id=EnvVar("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=EnvVar("AWS_SECRET_ACCESS_KEY"),
            region_name=EnvVar("AWS_REGION"),
        ),
    },
)
