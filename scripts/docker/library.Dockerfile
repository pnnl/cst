# Build runtime image
FROM cosim-ubuntu:latest AS cosim-library

ARG SIM_GID=9002
ARG SIM_GRP=runner
ARG SIM_UID
ARG COSIM_USER

RUN echo "===== Building CoSim Library =====" && \
  export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  apt-get update && \
  apt-get dist-upgrade -y && \
  apt-get install -y \
  sudo \
  pkgconf \
  build-essential \
  autoconf \
  libtool \
  libjsoncpp-dev \
  gfortran \
  cmake && \
  echo "root:${COSIM_USER}" | chpasswd && \
  addgroup --gid ${SIM_GID} ${SIM_GRP} && \
  useradd -m -s /bin/bash -g ${SIM_GRP} -G sudo,${SIM_GRP} -u $SIM_UID ${COSIM_USER} && \
  echo "${COSIM_USER}:${COSIM_USER}" | chpasswd
