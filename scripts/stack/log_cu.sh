#!/bin/bash

docker logs $(docker ps -q --filter "ancestor=cosim-jupyter:latest") 2>&1 | grep 'http://127.0.0.1:8888/lab?token' | tail -1