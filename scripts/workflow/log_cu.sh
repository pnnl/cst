#!/bin/bash

#docker logs $(docker ps -q --filter "ancestor=jupyter/minimal-notebook:7285848c0a11") 2>&1 | grep 'http://127.0.0.1' | tail -1
docker logs $(docker ps -q --filter "ancestor=cosim-jupyter:latest") 2>&1 | grep 'http://127.0.0.1' | tail -1