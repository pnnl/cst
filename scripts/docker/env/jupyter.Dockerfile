# Build runtime image
FROM jupyter/minimal-notebook:python-3.10

USER root

ENV GRANT_SUDO=yes

ENV SIM_UID=$SIM_UID
ENV SIM_USER=$SIM_USER
ENV SIM_HOST=$SIM_HOST
ENV SIM_WSL_HOST=$SIM_WSL_HOST
ENV SIM_WSL_PORT=$SIM_WSL_PORT
ENV SIM_DIR=$SIM_DIR

ENV COSIM_DB="$COSIM_DB"
ENV COSIM_USER="$COSIM_USER"
ENV COSIM_PASSWORD="$COSIM_PASSWORD"
ENV COSIM_HOME=$COSIM_HOME

ENV POSTGRES_HOST="$SIM_HOST"
ENV POSTGRES_PORT=$POSTGRES_PORT
ENV MONGO_HOST="$MONGO_HOST"

COPY . cosim_toolbox/

RUN echo "===== Building CoSim Jupyter =====" && \
  echo "<<<< Adding the '${COSIM_USER}' user >>>>" && \
  useradd -m -s /bin/bash -u $SIM_UID ${COSIM_USER} && \
  echo "<<<< Changing '${COSIM_USER}' password >>>>" && \
  echo "${COSIM_USER}:${COSIM_USER}" | chpasswd && \
  usermod -aG ${COSIM_USER} jovyan && \
  cp /home/jovyan/.bashrc ${COSIM_HOME}/.bashrc && \
  chown -R ${COSIM_USER}:${COSIM_USER} $COSIM_HOME && \
  cd cosim_toolbox || exit && \
  pip install --no-cache-dir -e . && \
  chown -R jovyan ../cosim_toolbox

USER jovyan
WORKDIR /home/jovyan

RUN echo "==" && \
# add the new finger print for each host connection
  mkdir -p .ssh && \
  touch .ssh/known_hosts && \
#  ssh-keyscan ${SIM_HOST} >> .ssh/known_hosts && \
  ssh-keygen -f copper-key-ecdsa -t ecdsa -b 521
# Line below needs to set at run for right now in the terminal to copy to 'authorized_keys' to user:
# ssh-copy-id -i copper-key-ecdsa ${SIM_USER}@${SIM_HOST}
