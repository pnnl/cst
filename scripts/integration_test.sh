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

#
# Start cosim stacks
#
echo "Starting Cosim stacks..."
source $COPPER_HOME/cosim.env
cd $COPPER_HOME/scripts/stack
./start_cu.sh
docker ps

#
# Run tests in local env
#
echo "Starting tests in local environment..."
source $COPPER_HOME/cosim.env
cd $COPPER_HOME/run/python/test_federation
rm -rf *.yaml *.log
export PYTHONPATH=.:$COPPER_HOME/src/cosim_toolbox
python runner.py
./runner.sh
docker ps
ps

#
# Run integration test validation
#
echo "Running integration test validation... "
cd $COPPER_HOME
make venv integration-test
