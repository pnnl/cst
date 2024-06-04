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
  echo "Usage: $0 <DEVOPS_SERVER>"
  echo " <DEVOPS_SERVER>: e.g. ecomp-devops.pnl.gov"
}

# Parse arguments
DEVOPS_SERVER=""

while [[ "$#" -gt 0 ]]; do
    case $1 in
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

echo "Update [$COSIM_ENV] with [$DEVOPS_SERVER]..."

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
