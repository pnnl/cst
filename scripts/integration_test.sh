#!/bin/bash

#
# Error handling:
# -e: script will exit on any command that returns a non-zero exit code
# -o pipefail: sets the exit code of a pipeline to that of the rightmost command to
#     exit with a non-zero status, or to zero if all commands of the pipeline exit successfully.
#
set -eo pipefail

# Function to display usage
usage() {
  echo "Usage: $0 <DEVOPS_SERVER> [-b|--build]"
  echo " -b, --build       Optional. Build images for jupyter, python, airflow by default"
}

# Parse arguments
BUILD_IMAGES=false
DEVOPS_SERVER=""

while [[ "$#" -gt 0 ]]; do
    case $1 in
        -b|--build) BUILD_IMAGES=true ;;
        *) if [[ -z "$DEVOPS_SERVER" ]]; then DEVOPS_SERVER="$1"; else echo "Unknown parameter passed: $1"; usage; exit 1; fi ;;
    esac
    shift
done

if [[ -z "$DEVOPS_SERVER" ]]; then
    echo "DEVOPS_SERVER argument not provided."
    usage
    exit 1
fi

COPPER_HOME=$(realpath ..)
COSIM_ENV=$COPPER_HOME/cosim.env

echo "Starting integration tests on [$DEVOPS_SERVER] with build images flag [$BUILD_IMAGES]..."

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

#
# Start cosim stacks
#
echo "Starting CoSim stacks..."
source $COPPER_HOME/cosim.env
cd $COPPER_HOME/scripts/stack
./stop_cu.sh
docker network prune -f
./start_cu.sh
docker ps

#
# Run tests in local env
#
echo "Starting tests in local environment..."
source $COPPER_HOME/cosim.env
cd $COPPER_HOME/run/python/test_federation
rm -rf *.yaml *.log
python runner.py
./runner.sh
docker ps

#
# Check test status
#
echo "Checking test status... TODO"

#
# Clean up
#
echo "Cleaning CoSim tests... Dummy operation for now"
#source $COPPER_HOME/cosim.env
#cd $COPPER_HOME/scripts/stack
#./stop_cu.sh
#docker network prune -f
#docker ps
#ps
