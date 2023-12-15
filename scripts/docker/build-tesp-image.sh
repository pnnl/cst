#!/bin/bash


images=(
  "tesp-build:latest"
  "tesp-helics:latest"
  "tesp-gridlabd:latest"
  "tesp-eplus:latest"
  "tesp-ns3:latest"
  "tesp-python:latest"
  "tesp-tespapi:latest"
)

files=(
  "tesp.Dockerfile"
  "helics.Dockerfile"
  "gridlabd.Dockerfile"
  "eplus.Dockerfile"
  "ns3.Dockerfile"
  "python.Dockerfile"
  "tespapi.Dockerfile"
)

export BUILDKIT_PROGRESS=plain

CONTEXT="./"

for i in "${!images[@]}"; do
#  clear
  IMAGE_NAME="${images[$i]}"
  DOCKERFILE="${files[$i]}"

  docker build --no-cache --rm \
               --network=host \
               -f ${DOCKERFILE} \
               -t ${IMAGE_NAME} ${CONTEXT}
done