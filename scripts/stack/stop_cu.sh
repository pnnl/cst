#!/bin/bash

# Shutdown and stop containers/volumes
# to remove all images as well  '--rmi all' add to docker compose below
# to remove all volumes as well  '--volumes' add to docker compose below
docker compose -f "$STACK_DIR/docker-compose.yaml" down --remove-orphans
docker compose -f "$STACK_DIR/timescale-docker-compose.yaml" down --remove-orphans

# to remove all volumes from stack
#docker volume rm stack_cst_mongo stack_cst_postgres -f
#docker volume prune -f
