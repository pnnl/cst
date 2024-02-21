#!/bin/bash

# Shutdown and stop containers/volumes
# to remove all images as well  '--rmi all' the docker compose
# to remove all volumes as well  '--volumes' er compose
docker-compose down --volumes --remove-orphans
