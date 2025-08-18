#!/bin/bash

#
# Error handling:
# -e: script will exit on any command that returns a non-zero exit code
# -o pipefail: sets the exit code of a pipeline to that of the rightmost command to
#     exit with a non-zero status, or to zero if all commands of the pipeline exit successfully.
#
set -eo pipefail

CID_ROOT=$(realpath ..)
CID_ENV=$CID_ROOT/cosim.env
source "$CID_ENV"

#
# Start cosim stacks
#
echo "Starting Cosim stacks..."
cd "$CID_ROOT/scripts/stack"
./start_db.sh
docker ps

#
# Run tests in local env
#
echo "Starting tests in local environment..."
cd "$CID_ROOT/run/python/test_federation"
rm -rf "*.sh" "*.yaml" "*.log"
export PYTHONPATH=.:$CID_ROOT/src/cosim_toolbox
python3 runner.py
if [ -f test_scenario.sh ]; then
  ./test_scenario.sh
fi

#
# Run integration test validation
#
echo "Running integration test validation... "
cd "$CID_ROOT"
make venv integration-test
