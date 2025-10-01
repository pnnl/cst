#!/bin/bash

#
# Error handling:
# -e: script will exit on any command that returns a non-zero exit code
# -o pipefail: sets the exit code of a pipeline to that of the rightmost command to
#     exit with a non-zero status, or to zero if all commands of the pipeline exit successfully.
#
set -eo pipefail

CID_ROOT=$(realpath ../..)
source "$CID_ROOT/cosim.env"

# Load configuration from config.sh
cd "$DOCKER_DIR"
source ./config.sh

# Remove log files from build directory
rm -f "$BUILD_DIR/*.logs" "$BUILD_DIR/out.txt"

export BUILDKIT_PROGRESS=plain

printf "==== Start building cosim images...\n"
for ((i = 0; i < ${#CONFIG_BUILDS[@]}; i+=3)); do
  name="${CONFIG_BUILDS[i]}"
  path="${CONFIG_BUILDS[i+1]}"
  build_flag="${CONFIG_BUILDS[i+2]}"
  printf "%s : %s\n" "$build_flag" "$BUILD"
  if [ "$build_flag" -eq "$BUILD" ]; then
    CONTEXT="$path"
    IMAGE_NAME="cosim-${name}:latest"
    DOCKERFILE="${name}.Dockerfile"

    printf "**** Creating %s from %s\n" "$IMAGE_NAME" "$DOCKERFILE"
    image1=$(docker images -q "${IMAGE_NAME}")
    docker build --no-cache --rm \
                 --build-arg CST_HOST="${CST_HOST}" \
                 --build-arg CST_GID=$CST_GID \
                 --build-arg CST_GRP="${CST_GRP}" \
                 --build-arg CST_UID=$CST_UID \
                 --build-arg CST_USER="${CST_USER}" \
                 --network=host \
                 -f "$DOCKERFILE" \
                 -t "$IMAGE_NAME" "$CONTEXT"
    image2=$(docker images -q "${IMAGE_NAME}")
    if [ "$image1" != "$image2" ]; then
      printf "Deleting old image Id: %s " "$image1"
#      docker rmi "${image1}"
    fi
  fi
done

cd "$CID_ROOT"
