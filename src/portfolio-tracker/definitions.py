from pathlib import Path

from dagster import Definitions
from dagster_dbt import DbtCliResource

from .assets import portfolio_tracker_dbt_assets

DBT_PROJECT_DIR = Path(__file__).resolve().parents[2] / "dbt"

defs = Definitions(
    assets=[portfolio_tracker_dbt_assets],
    resources={
        "dbt": DbtCliResource(project_dir=str(DBT_PROJECT_DIR)),
    },
)