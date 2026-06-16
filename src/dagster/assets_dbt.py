from dagster_dbt import DbtCliResource, dbt_assets

from .constants import DBT_PROJECT_DIR


dbt = DbtCliResource(project_dir=str(DBT_PROJECT_DIR))


@dbt_assets(manifest=DBT_PROJECT_DIR / "target" / "manifest.json")
def portfolio_tracker_dbt_assets(context, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()