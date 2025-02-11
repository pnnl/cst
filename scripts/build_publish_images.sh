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
source $CID_ENV

#
# Build new images
#
printf "Stop existing running stack...\n"
cd $CID_ROOT/scripts/stack
./stop_cu.sh
docker network prune -f

printf "Building Cosim Docker images locally with tag latest...\n"
cd $CID_ROOT/scripts/docker
./build-cosim-images.sh

# Load configuration from config.sh
source ./config.sh

# Tag and push images
tag_and_push_images() {
  local name path build_flag image_tag
  local commit_hash
  commit_hash=$(get_git_commit_hash)
  version=$(load_version)

  if [[ -z "$commit_hash" ]]; then
    exit 1
  fi

  for ((i = 0; i < ${#CONFIG_BUILDS[@]}; i+=3)); do
    name="${CONFIG_BUILDS[i]}"
    path="${CONFIG_BUILDS[i+1]}"
    build_flag="${CONFIG_BUILDS[i+2]}"

    local image_name="cosim-${name}:latest"
    image_tag="${IMAGE_PATH}cosim-${name}:${version}-${commit_hash}"

    printf "**** Tagging and publishing %s as %s\n" "$image_name" "$image_tag"
    docker tag "$image_name" "$image_tag"
    if ! docker push "$image_tag"; then
      printf "Failed to push %s\n" "$image_tag" >&2
      exit 1
    fi
  done
}

printf "==== Start tagging and publishing images...\n"
tag_and_push_images

printf "Build and publish images completed.\n"
