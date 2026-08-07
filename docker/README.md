# Docker

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
```

```bash
# Builds all services
docker compose -f docker/docker-compose.yml --env-file docker/.env.production up
docker compose -f docker/docker-compose.yml --env-file docker/.env.production up --build <service_name>
```

```bash
# Shell into any service
docker compose -f docker/docker-compose.yml --env-file docker/.env.production exec <service_name> bash
```

```bash
# Stop + remove containers and the network, keep volumes
docker compose -f docker/docker-compose.yml --env-file docker/.env.production down
docker compose -f docker/docker-compose.yml --env-file docker/.env.production down <service_name> # add -v to drop volumes
```
