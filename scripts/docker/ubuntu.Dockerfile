# Build runtime image
ARG UBUNTU=ubuntu
ARG UBUNTU_VERSION=:22.04

FROM ${UBUNTU}${UBUNTU_VERSION} AS cosim-ubuntu

RUN echo "===== Building Ubuntu =====" && \
  export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  apt-get update && \
  apt-get dist-upgrade -y
