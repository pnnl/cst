# Build runtime image
FROM jupyter/minimal-notebook:python-3.10

ARG CST_GID
ARG CST_GRP

USER root

ENV GRANT_SUDO=yes

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

COPY . /home/jovyan/cosim_toolbox/

RUN echo "===== Building CoSimulation Toolbox - Jupyter =====" && \
  addgroup --gid ${CST_GID} ${CST_GRP} && \
  usermod -g ${CST_GRP} jovyan && \
  chown -hR jovyan:$CST_GRP /home/jovyan/cosim_toolbox && \
  cd /home/jovyan/cosim_toolbox || exit && \
  pip install --no-cache-dir -e .

USER jovyan
WORKDIR /home/jovyan

RUN echo "==" && \
# add the new finger print for each host connection
  mkdir -p .ssh && \
  touch .ssh/known_hosts && \
#  ssh-keyscan ${CST_HOST} >> .ssh/known_hosts && \
  ssh-keygen -f copper-key-ecdsa -t ecdsa -b 521
# Line below needs to set at run for right now in the terminal to copy to 'authorized_keys' to user:
# ssh-copy-id -i copper-key-ecdsa ${LOCAL_USER}@${CST_HOST}
