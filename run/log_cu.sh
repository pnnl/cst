#!/bin/bash

docker logs $(docker ps -q --filter "ancestor=jupyter/minimal-notebook") 2>&1 | grep 'http://127.0.0.1' | tail -1