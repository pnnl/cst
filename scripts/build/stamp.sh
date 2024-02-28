#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  echo "Edit cosim.env in the Co-Simulation directory"
  echo "Then run 'source cosim.env' in that same directory"
  exit
fi

ver="22.04.1"
cosim_ver="1.0.0"

echo
echo "Stamping grid applications software $ver, if you want to change the version, edit this file."
echo "You should also update any documentation CHANGELOG.TXT or README.rst before stamping."
echo "The command below can show the branch and merge history to help you update documentation."
echo
echo "    git log --pretty=format:"%h %s" --graph"
echo

while true; do
    read -p "Are you ready to stamp Grid $ver? " yn
    case $yn in
        [Yy]* ) stamp="yes" break;;
        [Nn]* ) stamp="no"; break;;
        * ) echo "Please answer [y]es or [n]o.";;
    esac
done

if [[ $stamp == "no" ]]; then
  echo "Exiting grid applications software stamping"
  exit
fi

cd "${REPO_DIR}" || exit
echo "Stamping commit ids for:"
for dir in *
do
  if [ -d "$dir" ]; then
    repo=$dir/.git
    if [ -d "$repo" ]; then
      cd "$dir" || exit
      git rev-parse HEAD > "${BUILD_DIR}/$dir.id"
      git diff > "${BUILD_DIR}/$dir.patch"
      echo "...$dir"
      cd "${REPO_DIR}" || exit
    fi
  fi
done

#helics submodule in ns3
name="helics-ns3"
dir="${REPO_DIR}/ns-3-dev/contrib/helics"
if [ -d "$dir" ]; then
  cd "$dir" || exit
  git rev-parse HEAD > "${BUILD_DIR}/$name.id"
  git diff > "${BUILD_DIR}/$name.patch"
  echo "...$name"
  cd "${REPO_DIR}" || exit
fi

echo "Creating grid_binaries.zip for installed binaries for grid applications software"
cd "${INSTDIR}" || exit
zip -r -9 "${BUILD_DIR}/grid_binaries.zip" . &> "${BUILD_DIR}/grid_binaries.log" &

pip list > "${BUILD_DIR}/tesp_pypi.id"

echo "Stamping grid applications software $ver for install"
cd "${SIM_DIR}" || exit
echo "$ver" > "scripts/version"
echo "$cosim_ver" > "src/cosim_toolbox/version"

# un-comment for final version
# git tag "v$cosim_ver"

# for sampling cosim
echo "Creating CoSimulation Toolbox distribution package for pypi"
cd "${SIM_DIR}/src/cosim_toolbox" || exit
python3 -m build . > "${BUILD_DIR}/package.log"
echo "Checking CoSimulation Toolbox distribution package for pypi"
twine check dist/*
echo
echo "To upload the new CoSimulation Toolbox $ver pypi,"
echo "change directory to ${SIM_DIR}/src/cosim_toolbox"
echo "and run the command 'twine upload dist/*'"
echo
