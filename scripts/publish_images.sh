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

# Load configuration from config.sh
cd "$DOCKER_DIR"
source ./config.sh
cd ..

# Tag and push images
tag_and_push_images() {
  local name image_name image_tag image_tag2

  version=$(load_version)
  for ((i = 0; i < ${#CONFIG_BUILDS[@]}; i+=3)); do
    name="${CONFIG_BUILDS[i]}"

    image_name="cosim-${name}:latest"
    image_tag="pnnl/cst:${name}-latest"
    image_tag2="pnnl/cst:${name}-${version}"
#    image_tag3="pnnl/cst:${name}-${commit_hash}"

    printf "**** Tagging and publishing %s as %s\n" "$image_name" "$image_tag"
    docker tag "$image_name" "$image_tag"
    if ! docker push "$image_tag"; then
      printf "Failed to push %s\n" "$image_tag" >&2
      exit 1
    fi
    docker tag "$image_name" "$image_tag2"
    if ! docker push "$image_tag"; then
      printf "Failed to push %s\n" "$image_tag" >&2
      exit 1
    fi
    docker rmi "$image_tag" "$image_tag2"
  done
}

printf "==== Start tagging and publishing images...\n"
tag_and_push_images

printf "Build and publish images completed.\n"

cd "$CID_ROOT"