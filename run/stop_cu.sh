#!/bin/bash

# Shutdown and stop containers/volumes
# to remove all images as well add  '--rmi all' the docker compose
docker-compose -f airflow-docker-compose.yaml down --volumes
docker-compose -f postgres-docker-compose.yaml down --volumes

# Remove network and volumes 
# Comment out if you want it to persist
# sleep 10
# docker network rm cu_net
# docker volume rm cu_vol_user
# docker volume rm cu_vol_admin
