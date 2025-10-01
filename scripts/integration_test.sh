#!/bin/bash

#
# Error handling:
# -e: script will exit on any command that returns a non-zero exit code
# -o pipefail: sets the exit code of a pipeline to that of the rightmost command to
#     exit with a non-zero status, or to zero if all commands of the pipeline exit successfully.
#
set -eo pipefail

CID_ROOT=$(realpath ..)
source "$CID_ROOT/cosim.env"

#
# Start cosim stacks
#
printf "Starting Cosim stacks..."
cd "$CID_ROOT/scripts/stack"
./start_db.sh
#docker ps

#
# Run tests in local env
#
printf "Starting tests in local environment..."
cd "$CID_ROOT/run/python/test_federation"
rm -rf "*.sh" "*.yaml" "*.log"
export PYTHONPATH=.:$CID_ROOT/src/cosim_toolbox
python3 runner.py
if [ -f test_scenario.sh ]; then
  printf "Starting test_scenario..."
  ./test_scenario.sh
fi

#
# Run integration test validation
#
sleep 1m
printf "Running integration test validation... "
cd "$CID_ROOT"
make venv integration_tests

printf "Stoping Cosim stacks..."
cd "$CID_ROOT/scripts/stack"
./stop_db.sh

cd "$CID_ROOT"
