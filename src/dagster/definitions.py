from dagster import (
    Definitions,
    load_assets_from_modules
)
from dagster_dbt import DbtCliResource

from . import (
    assets_dbt,
    assets_prices
)
from .constants import DBT_PROJECT_DIR


defs = Definitions(
    assets=load_assets_from_modules(modules=[assets_dbt, assets_prices]),
    resources={
        "dbt": DbtCliResource(project_dir=str(DBT_PROJECT_DIR)),
    },
)
