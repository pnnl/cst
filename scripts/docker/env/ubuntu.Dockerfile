# Build runtime image
FROM ubuntu:24.04 AS cosim-ubuntu

ARG CST_GID
ARG CST_GRP

USER root

ENV LOCAL_UID=$LOCAL_UID
ENV LOCAL_USER=$LOCAL_USER

ENV CST_HOST="$CST_HOST"
ENV CST_WSL_HOST=$CST_WSL_HOST
ENV CST_WSL_PORT=$CST_WSL_PORT

ENV CST_UID=$CST_UID
ENV CST_USER=$CST_USER
ENV CST_PASSWORD=$CST_PASSWORD
ENV CST_HOME=$CST_HOME
ENV CST_ROOT=$CST_ROOT
ENV CST_DB=$CST_DB

ENV POSTGRES_HOST="$CST_HOST"
ENV POSTGRES_PORT=$POSTGRES_PORT
ENV MONGO_HOST="$MONGO_HOST"
ENV MONGO_PORT=$MONGO_PORT

COPY . /opt/cosim_toolbox

RUN echo "===== Building CoSimulation Toolbox - Ubuntu Docker =====" && \
  export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  apt-get update && \
  apt-get dist-upgrade -y && \
  apt-get install -y \
# python support
  python3 \
  python3-pip \
  python3-pil.imagetk && \
  echo "===== Adding user =====" && \
  echo "root:${CST_USER}" | chpasswd && \
  addgroup --gid ${CST_GID} ${CST_GRP} && \
  useradd -m -s /bin/bash -g ${CST_GRP} -G sudo,${CST_GRP} -u $CST_UID ${CST_USER} && \
  echo "${CST_USER}:${CST_USER}" | chpasswd && \
  echo "===== Installing CoSimulation Toolbox - Python =====" && \
  cd /opt/cosim_toolbox || exit && \
  pip install --break-system-packages --no-cache-dir . >> "$CST_HOME/pypi.log"
