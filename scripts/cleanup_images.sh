#!/bin/bash

COPPER_HOME=$(realpath ..)
COSIM_ENV=$COPPER_HOME/cosim.env
source $COSIM_ENV

# Load configuration from config.sh
source ./docker/config.sh

#
# Clean up old tagged images
#
cleanup_tagged_images() {
  local name path build_flag image_tag

  for ((i = 0; i < ${#CONFIG_BUILDS[@]}; i+=3)); do
    name="${CONFIG_BUILDS[i]}"
    path="${CONFIG_BUILDS[i+1]}"
    build_flag="${CONFIG_BUILDS[i+2]}"

    image_tag="${IMAGE_PATH}cosim-${name}"

    printf "**** Cleaning up %s\n" "$image_tag"

    # Delete the image with the specified tag
    images_to_delete=$(docker images --format "{{.Repository}}:{{.Tag}}" | grep "^${image_tag}")
    if [[ -n "$images_to_delete" ]]; then
      for img in $images_to_delete; do
        printf "Deleting image %s\n" "$img"
        docker rmi "$img"
      done
    else
      printf "No images found for %s\n" "$image_tag"
    fi
    printf "Done cleaning up %s\n\n" "$image_tag"
  done
}

# Function to delete <none> images or tags
cleanup_none_images() {
  # Find images with <none> as their repository or tag
  none_images=$(docker images --filter "dangling=true" -q)

  if [[ -z "$none_images" ]]; then
    printf "No <none> images found\n"
    return 0
  fi

  # Delete each <none> image
  for img in $none_images; do
    printf "Deleting image ID %s\n" "$img"
    docker rmi "$img"
  done

  printf "Cleanup of <none> images completed\n"
}

printf "======== Cleaning up tagged images...\n"
cleanup_tagged_images

printf "======== Cleaning up <none> images...\n"
cleanup_none_images
