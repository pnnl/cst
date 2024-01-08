ARG UBUNTU=ubuntu
ARG UBUNTU_VERSION=:20.04

FROM ${UBUNTU}${UBUNTU_VERSION} AS ubuntu-base

# User name and work directory
ENV USER_NAME=worker
ENV USER_HOME=/home/$USER_NAME

RUN export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  apt-get update && \
  echo "===== UPGRADING =====" && \
  apt-get dist-upgrade -y && \
  echo "===== INSTALL STUFF =====" && \
  apt-get install -y \
  sudo \
  wget \
  pkgconf \
  git \
  build-essential \
  autoconf \
  libtool \
  libjsoncpp-dev \
  gfortran \
  cmake \
  subversion \
  unzip \
  lsof \
  # Java support
  openjdk-11-jdk \
  # HELICS and FNCS support
  libzmq5-dev \
  libczmq-dev \
  libboost-dev \
  # for GridLAB-D
  libxerces-c-dev \
  libhdf5-serial-dev \
  libsuitesparse-dev \
  # end users replace libsuitesparse-dev with libklu1, which is licensed LGPL
  # for solvers Ipopt/cbc used by AMES/Agents
  coinor-cbc \
  coinor-libcbc-dev \
  coinor-libipopt-dev \
  liblapack-dev \
  libmetis-dev \
  # Python support
  python3.8 \
  python3.8-venv \
  python3-pip \
  python3-tk \
  python3-pil.imagetk && \
  ln -s /usr/lib/jvm/java-11-openjdk-amd64 /usr/lib/jvm/default-java && \
  echo "===== Clean Up =====" && \
  apt-get upgrade -y && \
  apt-get clean -y && \
  apt-get autoclean -y && \
  apt-get autoremove -y && \
  echo "root:worker" | chpasswd && \
  echo "<<<< Adding the 'worker' user >>>>" && \
  useradd -m -s /bin/bash ${USER_NAME} && \
  echo "<<<< Changing new user password >>>>" && \
  echo "${USER_NAME}:${USER_NAME}" | chpasswd && \
  usermod -aG sudo ${USER_NAME}
