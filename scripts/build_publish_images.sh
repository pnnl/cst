#!/bin/bash

#
# Error handling:
# -e: script will exit on any command that returns a non-zero exit code
# -o pipefail: sets the exit code of a pipeline to that of the rightmost command to
#     exit with a non-zero status, or to zero if all commands of the pipeline exit successfully.
#
set -eo pipefail

# Configuration
JSON_FILE="docker/versions.json"

# Check if jq is installed
if ! command -v jq &> /dev/null; then
  echo "jq could not be found. Please install jq to use this script."
  exit 1
fi

COPPER_HOME=$(realpath ..)
COSIM_ENV=$COPPER_HOME/cosim.env

#
# Build new images for jupyter, airflow and python by default
#
echo "Building CoSim Docker images..."
source $COSIM_ENV
cd $COPPER_HOME/scripts/docker
./build-cosim-images.sh

# Function to increment version
increment_version() {
  local VERSION=$1
  local PARTS=(${VERSION//./ })
  local MAJOR=${PARTS[0]}
  local MINOR=${PARTS[1]}
  local PATCH=${PARTS[2]}
  PATCH=$((PATCH + 1))
  echo "${MAJOR}.${MINOR}.${PATCH}"
}

# Read the image path from the JSON file
cd $COPPER_HOME/scripts
IMAGE_PATH=$(jq -r '.imagePath' $JSON_FILE)

# Flag to check if any versions were updated
VERSION_UPDATED=false

# Read the versions from the JSON file and iterate over each
jq -r '.versions | to_entries[] | "\(.key) \(.value)"' $JSON_FILE | while read -r IMAGE VERSION; do
  LOCAL_IMAGE="${IMAGE}:latest"
  REMOTE_IMAGE="${IMAGE_PATH}${IMAGE}:${VERSION}"

  # Check if the remote image exists
  if docker manifest inspect $REMOTE_IMAGE > /dev/null 2>&1; then
    # Diff the local and remote images
    if docker pull $REMOTE_IMAGE && [ "$(docker inspect --format='{{.Id}}' $LOCAL_IMAGE)" == "$(docker inspect --format='{{.Id}}' $REMOTE_IMAGE)" ]; then
      echo "No changes detected for $LOCAL_IMAGE compared to $REMOTE_IMAGE"
      continue
    else
      echo "Changes detected for $LOCAL_IMAGE compared to $REMOTE_IMAGE"
      NEW_VERSION=$(increment_version $VERSION)
      jq --arg image "$IMAGE" --arg version "$NEW_VERSION" '.versions[$image] = $version' $JSON_FILE > tmp.$$.json && mv tmp.$$.json $JSON_FILE
      VERSION_UPDATED=true
    fi
  else
    echo "Remote image not found: $REMOTE_IMAGE. Publishing new image."
  fi

  # Tag the image with the updated or existing version
  UPDATED_VERSION=$(jq -r --arg image "$IMAGE" '.versions[$image]' $JSON_FILE)
  NEW_IMAGE_TAG="${IMAGE_PATH}${IMAGE}:${UPDATED_VERSION}"
  docker tag $LOCAL_IMAGE $NEW_IMAGE_TAG
  docker push $NEW_IMAGE_TAG
done

# Commit and push the changes if any versions were updated
if [ "$VERSION_UPDATED" = true ]; then
  git add $JSON_FILE
  git commit -m "Build versions updated"
  git push
fi

echo "Build and publish images with comparison and version update process completed."
