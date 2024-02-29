#!/bin/bash

if [[ -z ${SIM_DIR} ]]; then
  echo "Edit cosim.env in the Co-Simulation directory"
  echo "Run 'source cosim.env' in that same directory"
  exit
fi

paths=(
  "./"
  "${SIM_DIR}/src/cosim_toolbox/"
  "${SIM_DIR}/src/cosim_toolbox/"
  "./"
  "${SIM_DIR}/scripts/build/"
  "./"
  "${SIM_DIR}/src/cosim_toolbox/"
  "./"
  "./"
  "/home/d3j331/tesp/repository/mesp/"
)

names=(
  "ubuntu"
  "jupyter"
  "airflow"
  "library"
  "build"
  "helics"
  "python"
  "tespapi"
  "julia"
  "mespapi"
)

builds=(
  1
  1
  1
  1
  1
  1
  1
  1
  1
  1
)

# Remove log files from build directory
rm -f "$BUILD_DIR/*.logs" "$BUILD_DIR/out.txt"
# Make directories and set permissions
cd "$SIM_DIR/run" || exit
mkdir -p ./dags ./logs ./plugins ./config ./python ../src/cosim_toolbox/cosim_toolbox.egg-info
# Make wide open for now
sudo chmod -R 777 ./dags ./logs ./plugins ./config ./python ../src

cd "$DOCKER_DIR" || exit
export BUILDKIT_PROGRESS=plain

for i in "${!names[@]}"; do
  CONTEXT="${paths[$i]}"
  IMAGE_NAME="cosim-${names[$i]}:latest"
  DOCKERFILE="${names[$i]}.Dockerfile"

  if [ "${builds[$i]}" -eq 1 ]; then
    echo "========"
    echo "Creating ${IMAGE_NAME} from ${DOCKERFILE}"
    image1=$(docker images -q "${IMAGE_NAME}")
    docker build --no-cache --rm \
                 --build-arg COSIM_USER="${COSIM_USER}" \
                 --build-arg SIM_HOST="${SIM_HOST}" \
                 --build-arg SIM_USER="${SIM_USER}" \
                 --build-arg SIM_UID=$SIM_UID \
                 --network=host \
                 -f "${DOCKERFILE}" \
                 -t "${IMAGE_NAME}" "${CONTEXT}"
    image2=$(docker images -q "${IMAGE_NAME}")
    if [ "$image1" != "$image2" ]; then
      echo "Deleting old image Id: $image1"
      docker rmi "${image1}"
    fi
    echo
  fi
done
