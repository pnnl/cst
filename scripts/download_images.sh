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

# Load configuration from config.sh
source ./docker/config.sh

printf "Stop existing running stack...\n"
cd $CID_ROOT/scripts/stack
./stop_db.sh
docker network prune -f

# Function to download images, delete existing local tags, and re-tag downloaded images
process_images() {
  local name path build_flag image_tag image_name
  local commit_hash version

  commit_hash=$(get_git_commit_hash)
  version=$(load_version)

  if [[ -z "$commit_hash" || -z "$version" ]]; then
    printf "Invalid git commit hash %s or version %s\n" "$commit_hash" "$version" >&2
    exit 1
  fi

  for ((i = 0; i < ${#CONFIG_BUILDS[@]}; i+=3)); do
    name="${CONFIG_BUILDS[i]}"
    path="${CONFIG_BUILDS[i+1]}"
    build_flag="${CONFIG_BUILDS[i+2]}"

    image_tag="${IMAGE_PATH}cosim-${name}:${version}-${commit_hash}"
    image_name="cosim-${name}:latest"

    printf "**** Downloading and processing %s\n" "$image_tag"

    # Download the image with the specified tag
    if ! docker pull "$image_tag"; then
      printf "Failed to pull image %s\n" "$image_tag" >&2
      exit 1
    fi

    # Retag the downloaded image to replace 'latest'
    printf "Retagging %s to %s\n" "$image_tag" "$image_name"
    docker tag "$image_tag" "$image_name"
    printf "Done processing %s\n\n" "$image_tag"
  done
}

# Execute the image processing function
printf "==== Start downloading and processing images...\n"
process_images
