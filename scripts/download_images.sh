#!/bin/bash

# Configuration
JSON_FILE="docker/versions.json"

# Check if jq is installed
if ! command -v jq &> /dev/null; then
  echo "jq could not be found. Please install jq to use this script."
  exit 1
fi

# Read the image path from the JSON file
IMAGE_PATH=$(jq -r '.imagePath' $JSON_FILE)

# Read the versions from the JSON file and iterate over each
jq -r '.versions | to_entries[] | "\(.key) \(.value)"' $JSON_FILE | while read -r IMAGE VERSION; do
  FULL_IMAGE_PATH="${IMAGE_PATH}${IMAGE}:${VERSION}"

  # Check if the image exists in the registry
  if docker manifest inspect $FULL_IMAGE_PATH > /dev/null 2>&1; then
    echo "Pulling image: $FULL_IMAGE_PATH"
    docker pull $FULL_IMAGE_PATH
  else
    echo "Image not found: $FULL_IMAGE_PATH"
  fi
done

echo "Script execution completed."
