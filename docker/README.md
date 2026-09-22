# Docker

## Required EnvVars in `.env`

```bash
MOTHERDUCK_DB_PATH=
MOTHERDUCK_TOKEN=
POSTGRES_USER="dagster_postgres_user"
POSTGRES_PASSWORD="dagster_postgres_password"
POSTGRES_DB="dagster_postgres_db"
```

## Full steps for single Docker container setup on `streamlit_app`

```bash
# From project root
docker build --no-cache -f docker/DockerFile_streamlit -t streamlit_app .
docker images
docker run -d -p 8501:8501 --name streamlit_app streamlit_app:latest (or use <IMAGE_ID>)
```

To enter container CLI

```bash
docker ps
docker exec -it <CONTAINER_ID> /bin/bash
```

## Steps for Docker Compose

View the resolved compose configs

```bash
# From project root
docker compose -f docker/docker-compose.yml --env-file docker/.env.production config
# Or cd into docker and run simpler commands
docker compose config
```

```bash
# Builds all services
docker compose up
docker compose up --build <service_name>
```

```bash
# Shell into any service
docker compose exec <service_name> bash
```

```bash
# Stop + remove containers and the network, keep volumes
docker compose down
docker compose down <service_name> # add -v to drop volumes
```
