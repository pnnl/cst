#!/bin/bash

# Copyright (c) 2021-2023 Battelle Memorial Institute
# file: grid_apps.sh

if [[ -z ${INSTDIR} ]]; then
  echo
  echo "To build a local environment:"
  echo "  Edit cosim.env in the CoSimulation Toolbox directory"
  echo "  Define LOCAL_ENV other than a blank in that file"
  echo "  Run 'source cosim.env' in that same directory"
  echo "  Run './scripts/grid_apps.sh [git login] [git email]' in that same directory"
  echo
  exit
fi

# You should get familiar with the command line to have good success with CoSimulation Toolbox
# As such, you may want to run in remote shh terminal.
# Here is to how to install and configured ssh server
#   sudo apt-get -y install openssh-server
#   sudo nano /etc/ssh/sshd_config
# Once you open the file, find and change the uncomment line: # Port 22
#   sudo service ssh start
#   sudo systemctl status ssh

# If you would to use and IDE here's to install snap Pycharm IDE for python
#   sudo snap install pycharm-community --classic
# Here is how to start env and pycharm and capture pycharm log for any errors
#   source ~home/copper/cosim.env
#   pycharm-community &> ~/charm.log&

#alternatives command line for java or python
#sudo update-alternatives --config java

# Check for the presence of the binary build flag in command arguments
binary_flag=""
if [[ "$3" == "-y" ]]; then
  binary_flag="Y"
elif [[ "$3" == "-n" ]]; then
  binary_flag="N"
fi

if [[ -z "$binary_flag" ]]; then
  # Ask the user if the flag is not set via command arguments
  while true; do
      read -p "Do you wish to build the binaries? (Yy/Nn)" yn
      case $yn in
          [Yy]* ) binaries="develop"; break;;
          [Nn]* ) binaries="copy"; break;;
          * ) echo "Please answer [y]es or [n]o.";;
      esac
  done
else
  # Set binaries based on the command argument
  case $binary_flag in
      [Yy]* ) binaries="develop";;
      [Nn]* ) binaries="copy";;
  esac
  echo "Binaries setting chosen through command argument: $binaries"
fi

echo "Binaries setting: $binaries; username: $1; email: $2"

if [[ $binaries == "develop" ]]; then
# add build tools OS
sudo apt-get -y upgrade
sudo apt-get -y install pkgconf \
git \
build-essential \
autoconf \
libtool \
libjsoncpp-dev \
gfortran \
install cmake \
subversion
fi

# add tools/libs for Java support, HELICS, FNCS, GridLAB-D, Ipopt/cbc
sudo apt-get -y install openjdk-11-jdk \
unzip \
libzmq5-dev \
libczmq-dev \
libboost-dev \
libxerces-c-dev \
libhdf5-serial-dev \
libsuitesparse-dev \
coinor-cbc \
coinor-libcbc-dev \
coinor-libipopt-dev \
liblapack-dev \
libmetis-dev \
python3.12-venv \
python3-pip \
python3-tk \
python3-pil.imagetk

sudo ln -sf /usr/lib/jvm/java-11-openjdk-amd64 /usr/lib/jvm/default-java

echo
if [[ -z $1 && -z $2 ]]; then
  echo "No user name set for git repositories!"
else
  git config --global user.name "$1"
  git config --global user.email "$2"
  echo "User .name=$1 and .email=$2 have been set for git repositories!"
fi
git config --global credential.helper store

cd "${HOME}" || exit
echo "Install environment to $HOME/grid"
mkdir -p grid
cd grid || exit

echo
echo "Install a virtual python environment to $HOME/grid/venv"
python3 -m pip install --upgrade pip
python3 -m pip install virtualenv
"${HOME}/.local/bin/virtualenv" venv --prompt GRID

echo
echo "Install executables environment to $HOME/grid/tenv"
mkdir -p tenv

echo
echo "Install grid applications software to $HOME/grid/repo"
mkdir -p repo
cd repo || exit

echo
echo "Download all relevant repositories..."
if [[ $binaries == "develop" ]]; then

#  echo
#  echo ++++++++++++++ TESP
#  if [[ -d "${REPO_DIR}/tesp" ]]; then
#    git clone -b develop https://github.com/pnnl/tesp.git
#    "${BUILD_DIR}/patch.sh" tesp tesp
#  fi
#
#  echo
#  echo ++++++++++++++ MESP
#  if [[ -d "${REPO_DIR}/mesp" ]]; then
#    echo ""
#    # git clone -b develop https://github.com/pnnl/mesp.git
#    # "${BUILD_DIR}/patch.sh" mesp mesp
#  fi
#
#  echo
#  echo ++++++++++++++ PSST
#  if [[ -d "${REPO_DIR}/AMES-V5.0" ]]; then
#    # git clone -b master https://github.com/ames-market/psst.git
#    # For dsot
#    git clone -b master https://github.com/ames-market/AMES-V5.0.git
#    "${BUILD_DIR}/patch.sh" AMES-V5.0 AMES-V5.0
#  fi
#
#  echo
#  echo ++++++++++++++ FNCS
#  if [[ -d "${REPO_DIR}/fncs" ]]; then
#    git clone -b feature/opendss https://github.com/FNCS/fncs.git
#    # For different calling no cpp
#    # git clone -b develop https://github.com/FNCS/fncs.git
#    "${BUILD_DIR}/patch.sh" fncs fncs
#  fi

  echo
  echo ++++++++++++++ HELICS
  if [[ -d "${REPO_DIR}/HELICS-src" ]]; then
    git clone -b main https://github.com/GMLC-TDC/HELICS-src
    "${BUILD_DIR}/patch.sh" HELICS-src HELICS-src
  fi

  echo
  echo ++++++++++++++ GRIDLAB
  if [[ -d "${REPO_DIR}/gridlab-d" ]]; then
    git clone -b master https://github.com/gridlab-d/gridlab-d.git
    "${BUILD_DIR}/patch.sh" gridlab-d gridlab-d
  fi

#  echo
#  echo ++++++++++++++ ENERGYPLUS
#  if [[ -d "${REPO_DIR}/EnergyPlus" ]]; then
#    git clone -b fncs_9.3.0 https://github.com/FNCS/EnergyPlus.git
#    "${BUILD_DIR}/patch.sh" EnergyPlus EnergyPlus
#  fi
#
#  echo
#  echo ++++++++++++++ NS-3
#  if [[ -d "${REPO_DIR}/gridlab-d" ]]; then
#    git clone -b master https://gitlab.com/nsnam/ns-3-dev.git
#    "${BUILD_DIR}/patch.sh" ns-3-dev ns-3-dev
#  fi
#
#  echo
#  echo ++++++++++++++ HELICS-NS-3
#  if [[ -d "${REPO_DIR}/gridlab-d" ]]; then
#    git clone -b main https://github.com/GMLC-TDC/helics-ns3 ns-3-dev/contrib/helics
#    "${BUILD_DIR}/patch.sh" ns-3-dev/contrib/helics helics-ns3
#  fi

  echo
  echo ++++++++++++++ KLU SOLVER
  unzip -q "${BUILD_DIR}/KLU_DLL.zip" -d ./KLU_DLL
fi

# Compile all relevant executables
cd "${BUILD_DIR}" || exit
./build_c.sh $binaries
