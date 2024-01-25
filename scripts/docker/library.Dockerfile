# Build runtime image
ARG UBUNTU=ubuntu
ARG UBUNTU_VERSION=:22.04

FROM ${UBUNTU}${UBUNTU_VERSION} AS cosim-library

# User name and work directory
ARG UID
ARG COSIM_USER
ENV COSIM_HOME=/home/$COSIM_USER

RUN echo "===== Building CoSim Library =====" && \
  export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  echo "===== Install Libraries =====" && \
  apt-get update && \
  apt-get dist-upgrade -y && \
  apt-get install -y software-properties-common && \
  add-apt-repository ppa:deadsnakes/ppa -y && \
  apt-get update && \
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
  python3.8-tk \
  python3-pil.imagetk && \
  ln -s /usr/lib/jvm/java-11-openjdk-amd64 /usr/lib/jvm/default-java && \
  echo "root:worker" | chpasswd && \
  echo "<<<< Adding the 'worker' user >>>>" && \
  useradd -m -s /bin/bash -u $UID ${COSIM_USER} && \
  echo "<<<< Changing new user password >>>>" && \
  echo "${COSIM_USER}:${COSIM_USER}" | chpasswd && \
  usermod -aG sudo ${COSIM_USER}
