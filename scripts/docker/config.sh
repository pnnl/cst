#!/bin/bash

if [[ -z ${SIM_DIR} ]]; then
  echo "Edit cosim.env in the top directory"
  echo "Run 'source cosim.env' in that same directory"
  exit 1
fi

# BUILD: to build image
# SKIP: skip building image
BUILD=1
SKIP=0

CONFIG_BUILDS=(
  "ubuntu" "./" $SKIP
  "jupyter" "${SIM_DIR}/src/cosim_toolbox/" $SKIP
  "airflow" "${SIM_DIR}/src/cosim_toolbox/" $SKIP
  "library" "./" $SKIP
  "build" "${SIM_DIR}/scripts/build/" $BUILD
  "helics" "./" $BUILD
  "python" "${SIM_DIR}/src/cosim_toolbox/" $SKIP
)

# Image full path on the remote registry
IMAGE_PATH="devops-registry.pnnl.gov/e-comp/thrust-3/copper/"

# Version file
VERSION_FILE="${SIM_DIR}/src/cosim_toolbox/version"

# Function to get the latest git commit hash (first 8 characters)
get_git_commit_hash() {
  local commit_hash
  commit_hash=$(git rev-parse --short=8 HEAD)
  if [[ -z "$commit_hash" ]]; then
    printf "Failed to get git commit hash\n" >&2
    return 1
  fi
  printf "%s" "$commit_hash"
}

# Function to load version from a file and return the version
load_version() {
  if [[ ! -f $VERSION_FILE ]]; then
    printf "Version file %s not found\n" "$VERSION_FILE" >&2
    return 1
  fi
  version=$(<"$VERSION_FILE")
  if [[ -z "$version" ]]; then
    printf "Failed to load version file %s\n" "$VERSION_FILE" >&2
    return 1
  fi
  printf "%s" "$version"
}
