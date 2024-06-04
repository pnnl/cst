#!/bin/bash

#
# Error handling:
# -e: script will exit on any command that returns a non-zero exit code
# -o pipefail: sets the exit code of a pipeline to that of the rightmost command to
#     exit with a non-zero status, or to zero if all commands of the pipeline exit successfully.
#
set -eo pipefail


COPPER_HOME=$(realpath ..)
COSIM_ENV=$COPPER_HOME/cosim.env

echo "Starting integration tests on [$DEVOPS_SERVER]..."


#
# Update environment
#
if [[ "$OSTYPE" == "darwin"* ]]; then
  # macOS system
  SED_CMD=(-i '' 's/^export SIM_HOST=.*/export SIM_HOST='"$DEVOPS_SERVER"'/')
else
  # Assuming Linux
  SED_CMD=(-i 's/^export SIM_HOST=.*/export SIM_HOST='"$DEVOPS_SERVER"'/')
fi
sed "${SED_CMD[@]}" "$COSIM_ENV"

#
# Build new images for jupyter, airflow and python by default
#
if $BUILD_IMAGES; then
    echo "Building CoSim Docker images..."
    source $COSIM_ENV
    cd $COPPER_HOME/scripts/docker
    ./build-cosim-images.sh
else
    echo "Skipping building of CoSim Docker images."
fi