# Full steps for Docker Setup

```bash
docker build --no-cache -f .devcontainer/DockerFile -t portfolio-tracker-app .
docker images
docker run -d -p 8501:8501 --name portfolio-tracker-app portfolio-tracker-app:latest (or use <IMAGE_ID>)
```

To enter container CLI

```bash
docker ps
docker exec -it <CONTAINER_ID> /bin/bash
```
