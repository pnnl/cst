#!/bin/bash

paths=(
  "./"
  "/home/d3j331/tesp/repository/copper/scripts/builder/"
  "./"
  "./"
  "./"
  "./"
  "/home/d3j331/tesp/repository/copper/src/cosim_toolbox/"
  "./"
  "./"
  "/home/d3j331/tesp/repository/mesp/"
)

images=(
  "cosim-library:latest"
  "cosim-build:latest"
  "cosim-helics:latest"
  "cosim-gridlabd:latest"
  "cosim-eplus:latest"
  "cosim-ns3:latest"
  "cosim-python:latest"
  "cosim-tespapi:latest"
  "cosim-julia:latest"
  "cosim-mespapi:latest"
)

files=(
  "library.Dockerfile"
  "build.Dockerfile"
  "helics.Dockerfile"
  "gridlabd.Dockerfile"
  "eplus.Dockerfile"
  "ns3.Dockerfile"
  "python.Dockerfile"
  "tespapi.Dockerfile"
  "julia.Dockerfile"
  "mespapi.Dockerfile"
)

builds=(
  0
  0
  0
  1
  1
  1
  1
  1
  1
  1
)

export BUILDKIT_PROGRESS=plain

for i in "${!images[@]}"; do
#  clear
  CONTEXT="${paths[$i]}"
  IMAGE_NAME="${images[$i]}"
  DOCKERFILE="${files[$i]}"

  if [ "${builds[$i]}" -eq 1 ]; then
    echo "${DOCKERFILE}"
    docker build --no-cache --rm \
                 --build-arg UID=$UID \
                 --network=host \
                 -f "${DOCKERFILE}" \
                 -t "${IMAGE_NAME}" "${CONTEXT}"
  fi

done