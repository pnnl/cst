#!/bin/bash

# Shutdown and stop containers/volumes
# to remove all images as well  '--rmi all' the docker compose
# to remove all volumes as well  '--volumes' er compose
docker-compose -f docker-compose.yaml down --volumes
docker-compose -f postgres-docker-compose.yaml down --volumes
docker rm -f mongodb

# Remove network and volumes 
# Comment out if you want it to persist
# sleep 10
# docker network rm cu_net
# docker volume rm cu_vol_user
# docker volume rm cu_vol_admin
