# Portfolio-Tracker

This repository contains all the code and documentation used for portfolio-tracker.

## Installation with `uv`

If you need to install `uv`, refer to this [page](https://docs.astral.sh/uv/getting-started/installation/).

```shell
uv sync
```

## Required Environment Variables

Create a `.env` file in the root folder with the following environmental variables.

```shell
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=
DBT_ENGINE_PROFILES_DIR=$PWD/dbt
DBT_PROJECT_DIR=$PWD/dbt
MOTHERDUCK_DB_PATH="md:portfolio_tracker"  # Create this database in MotherDuck
MOTHERDUCK_TOKEN=
```

## Running Dagster Ingestion

UI

```shell
dagster dev -w workspace.yaml
```

Headless

```shell
dagster-daemon run
dagster job execute -j <job_name>> -w workspace.yaml
```
