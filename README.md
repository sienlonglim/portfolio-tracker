# Portfolio-Tracker

This repository contains all the code and documentation used for portfolio-tracker.

## Installation with `uv`

If you need to install `uv`, refer to this [page](https://docs.astral.sh/uv/getting-started/installation/).
Sync with dependencies and create `.venv`

```shell
uv sync
```

For LightDash, a virtual environment for node and npm are recommended.

```shell
nodeenv .nenv
source .nenv/bin/activate
npm install -g @lightdash/cli
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
dagster dev
```

Headless

```shell
dg launch --job <job_name> # job_dbt_build or job_ingest_daily_stock_prices
```

## Running LightDash

TBC
