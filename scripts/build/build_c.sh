#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  echo "Edit cosim.env in the Co-Simulation directory"
  echo "Then please run 'source cosim.env' in that same directory"
  exit
fi

echo
echo "++++++++++++++  Compiling and Installing Grid applications software is starting!  ++++++++++++++"
echo

echo "Activate Virtual Environment..."
. "$REPO_DIR/venv/bin/activate"
echo "Installing Python Libraries..."
which python > "${BUILD_DIR}/tesp_pypi.log" 2>&1
pip install --upgrade pip >> "${BUILD_DIR}/tesp_pypi.log" 2>&1
pip install -r "${TESPDIR}/requirements.txt" >> "${BUILD_DIR}/tesp_pypi.log" 2>&1

echo "Installing Python TESP API..."
cd "${TESPDIR}/src/tesp_support" || exit
pip install -e . > "${BUILD_DIR}/tesp_api.log" 2>&1

echo "Installing Python PSST..."
cd "${REPO_DIR}/AMES-V5.0/psst" || exit
pip install -e . > "${BUILD_DIR}/AMES-V5.0.log" 2>&1

#  pip install tesp_support --upgrade
#  pip install psst --upgrade

cd "${BUILD_DIR}" || exit
if [[ $1 == "develop" ]]; then

  echo "Compiling and Installing FNCS..."
  ./fncs_b.sh clean > fncs.log 2>&1

  echo "Compiling and Installing FNCS for Java..."
  ./fncs_j_b.sh clean > fncs_j.log 2>&1

  echo "Compiling and Installing HELICS..."
  ./HELICS-src_b.sh clean > HELICS-src.log 2>&1

  echo "Compiling and Installing KLU..."
  ./KLU_DLL_b.sh clean > KLU_DLL.log 2>&1

  echo "Compiling and Installing Gridlabd..."
  ./gridlab-d_b.sh clean > gridlab-d.log 2>&1

  echo "Compiling and Installing EnergyPlus..."
  ./EnergyPlus_b.sh clean > EnergyPlus.log 2>&1

  echo "Compiling and Installing EnergyPlus for Java..."
  ./EnergyPlus_j_b.sh clean > EnergyPlus_j.log 2>&1

  echo "Compiling and Installing NS-3..."
  ./ns-3-dev_b.sh clean > ns-3-dev.log 2>&1

  echo "Compiling and Installing Ipopt with ASL and Mumps..."
  ./ipopt_b.sh clean > ipopt.log 2>&1

  echo "Compiling and Installing TESP EnergyPlus agents and TMY converter..."
  ./tesp_b.sh clean > tesp.log 2>&1

else

  ver=$(cat "${BUILD_DIR}/version")
  echo "Installing HELICS, FNCS, GridLabD, EnergyPlus, NS3, and solver binaries..."
  cd "${INSTDIR}" || exit
  wget --no-check-certificate https://github.com/pnnl/tesp/releases/download/${ver}/grid_binaries.zip
  unzip grid_binaries.zip > "${BUILD_DIR}/grid_binaries.log" 2>&1
  rm grid_binaries.zip
fi

cd "${BUILD_DIR}" || exit
echo "Installing HELICS Python bindings..."
./HELICS-py.sh clean > HELICS-py.log 2>&1

echo "Installing TESP documentation..."
./docs_b.sh clean > docs.log 2>&1

# Creates the necessary links and cache to the most recent shared libraries found
# in the directories specified on the command line, in the file /etc/ld.so.conf,
# and in the trusted directories (/lib and /usr/lib).
sudo ldconfig
echo
echo "Grid application installation logs are found in ${BUILD_DIR}"
echo "++++++++++++++  Compiling and Installing Grid applications software is complete!  ++++++++++++++"

cd "${BUILD_DIR}" || exit
./versions.sh

echo
echo "++++++++++++++  Grid applications has been installed! That's all folks!  ++++++++++++++"
echo