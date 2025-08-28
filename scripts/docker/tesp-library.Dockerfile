# Build runtime image
FROM cosim-ubuntu:latest AS cosim-library

ARG CST_GID
ARG CST_GRP
ARG CST_UID
ARG CST_USER

RUN echo "===== Building CoSimulation Toolbox - Library =====" && \
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
  echo "root:${CST_USER}" | chpasswd && \
  addgroup --gid ${CST_GID} ${CST_GRP} && \
  useradd -m -s /bin/bash -g ${CST_GRP} -G sudo,${CST_GRP} -u $CST_UID ${CST_USER} && \
  echo "${CST_USER}:${CST_USER}" | chpasswd
