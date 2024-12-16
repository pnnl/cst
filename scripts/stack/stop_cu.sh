#!/bin/bash

# Shutdown and stop containers/volumes
# to remove all images as well  '--rmi all' the docker compose
# to remove all volumes as well  '--volumes' er compose
docker compose down --volumes --remove-orphans

# to remove all volumes from stack
docker volume rm stack_cu_mongo stack_cu_postgres -f
docker volume prune -f