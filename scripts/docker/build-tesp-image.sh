#!/bin/bash

images=(
#  "tesp-library:latest"
#  "tesp-build:latest"
#  "tesp-helics:latest"
#  "tesp-gridlabd:latest"
#  "tesp-eplus:latest"
#  "tesp-ns3:latest"
#  "tesp-python:latest"
#  "tesp-tespapi:latest"
#  "mesp-julia:latest"
  "mesp-mespapi:latest"
)

files=(
#  "library.Dockerfile"
#  "build.Dockerfile"
#  "helics.Dockerfile"
#  "gridlabd.Dockerfile"
#  "eplus.Dockerfile"
#  "ns3.Dockerfile"
#  "python.Dockerfile"
#  "tespapi.Dockerfile"
#  "julia.Dockerfile"
  "mespapi.Dockerfile"
)

export BUILDKIT_PROGRESS=plain

CONTEXT="./../"

for i in "${!images[@]}"; do
#  clear
  IMAGE_NAME="${images[$i]}"
  DOCKERFILE="${files[$i]}"

# --build-arg name=$Baeldung

  docker build --no-cache --rm \
               --network=host \
               -f ${DOCKERFILE} \
               -t ${IMAGE_NAME} ${CONTEXT}

done