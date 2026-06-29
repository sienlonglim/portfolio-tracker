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
from .constants import DBT_PROJECT_DIR, DBT_PROFILE_DIR
from .jobs import jobs
from .resources import MotherDuckS3Resource

assert DBT_PROJECT_DIR.exists()
assert (DBT_PROFILE_DIR / "profiles.yml").exists()

defs = Definitions(
    assets=load_assets_from_modules(modules=[assets_dbt, assets_prices]),
    asset_checks=[
        assets_prices.test__stock_open_close_prices_not_empty,
        assets_prices.test__stock_open_close_prices_has_required_columns
    ],
    jobs=jobs,
    resources={
        "dbt": DbtCliResource(
            project_dir=str(DBT_PROJECT_DIR),
            profiles_dir=str(DBT_PROFILE_DIR),
            profile="dbt-portfolio-tracker",
            target="prod",
            global_config_flags=["--debug"],
        ),
        "s3": S3Resource(
            aws_access_key_id=EnvVar("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=EnvVar("AWS_SECRET_ACCESS_KEY"),
            region_name=EnvVar("AWS_REGION"),
        ),
        "motherduck": MotherDuckS3Resource(
            motherduck_token=EnvVar("MOTHERDUCK_TOKEN"),
            aws_access_key_id=EnvVar("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=EnvVar("AWS_SECRET_ACCESS_KEY"),
            aws_region=EnvVar("AWS_REGION"),
        )
    },
)
