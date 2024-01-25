#!/bin/bash

paths=(
  "/home/d3j331/tesp/repository/copper/src/cosim_toolbox/"
  "/home/d3j331/tesp/repository/copper/src/cosim_toolbox/"
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

names=(
  "jupyter"
  "airflow"
  "library"
  "build"
  "helics"
  "gridlabd"
  "eplus"
  "ns3"
  "python"
  "tespapi"
  "julia"
  "mespapi"
)

builds=(
  1
  1
  1
  1
  1
  1
  1
  1
  1
  1
  1
  1
)

export BUILDKIT_PROGRESS=plain

for i in "${!names[@]}"; do
  CONTEXT="${paths[$i]}"
  IMAGE_NAME="cosim-${names[$i]}:latest"
  DOCKERFILE="${names[$i]}.Dockerfile"

  if [ "${builds[$i]}" -eq 1 ]; then
    echo "========"
    echo "Creating ${IMAGE_NAME} from ${DOCKERFILE}"
    image1=$(docker images -q "${IMAGE_NAME}")
    docker build --no-cache --rm \
                 --build-arg UID=$UID \
                 --build-arg COSIM_USER="${COSIM_USER}" \
                 --build-arg DOCKER_HOST="$(cat /etc/hostname)" \
                 --build-arg DOCKER_USER="$(USER)" \
                 --network=host \
                 -f "${DOCKERFILE}" \
                 -t "${IMAGE_NAME}" "${CONTEXT}"
    image2=$(docker images -q "${IMAGE_NAME}")
    if [ "$image1" != "$image2" ]; then
      echo "Deleting old image Id: $image1"
      docker rmi "${image1}"
    fi
    echo
  fi
done
