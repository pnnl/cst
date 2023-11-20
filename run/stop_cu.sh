#!/bin/bash

# Shutdown and stop containers/volumes
docker-compose -f airflow-docker-compose.yaml down --volumes --rmi all
docker-compose -f postgres-docker-compose.yaml down --volumes --rmi all

# Remove network and volumes 
# Comment out if you want it to persist in docker for next
sleep 10
# docker network rm cu_net
# docker volume rm cu_vol_user
# docker volume rm cu_vol_admin
