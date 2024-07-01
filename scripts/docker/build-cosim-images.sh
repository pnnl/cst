#!/bin/bash

#
# Error handling:
# -e: script will exit on any command that returns a non-zero exit code
# -o pipefail: sets the exit code of a pipeline to that of the rightmost command to
#     exit with a non-zero status, or to zero if all commands of the pipeline exit successfully.
#
set -eo pipefail

# Load configuration from config.sh
source ./config.sh

# Remove log files from build directory
rm -f "$BUILD_DIR/*.logs" "$BUILD_DIR/out.txt"

# Make directories and set permissions
cd "$SIM_DIR/run"
mkdir -p ./dags ./logs ./plugins ./config ./python ../src/cosim_toolbox/cosim_toolbox.egg-info
# Make wide open for now
sudo chmod -R 777 ./dags ./logs ./plugins ./config ./python ../src

cd "$DOCKER_DIR"
export BUILDKIT_PROGRESS=plain

printf "==== Start building cosim images...\n"
for ((i = 0; i < ${#CONFIG_BUILDS[@]}; i+=3)); do
  name="${CONFIG_BUILDS[i]}"
  path="${CONFIG_BUILDS[i+1]}"
  build_flag="${CONFIG_BUILDS[i+2]}"

  if [ "$build_flag" -eq $BUILD ]; then
    CONTEXT="$path"
    IMAGE_NAME="cosim-${name}:latest"
    DOCKERFILE="${name}.Dockerfile"

    printf "**** Creating %s from %s\n" "$IMAGE_NAME" "$DOCKERFILE"
    docker build --no-cache --rm \
                 --build-arg COSIM_USER="${COSIM_USER}" \
                 --build-arg SIM_HOST="${SIM_HOST}" \
                 --build-arg SIM_USER="${SIM_USER}" \
                 --build-arg SIM_UID=$SIM_UID \
                 --network=host \
                 -f "$DOCKERFILE" \
                 -t "$IMAGE_NAME" "$CONTEXT"
  fi
done
