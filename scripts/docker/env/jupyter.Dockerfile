# Build runtime image
FROM jupyter/minimal-notebook:7285848c0a11

USER root

ENV SIM_USER=$SIM_USER
ENV SIM_HOST=$SIM_HOST
ENV SIM_DIR=$SIM_DIR

ENV COSIM_DB="$COSIM_DB"
ENV COSIM_USER="$COSIM_USER"
ENV COSIM_PASSWORD="$COSIM_PASSWORD"
ENV COSIM_HOME=$COSIM_HOME

ENV POSTGRES_HOST="$SIM_HOST"
ENV POSTGRES_PORT=$POSTGRES_PORT
ENV MONGO_HOST="$MONGO_HOST"

ENV GRANT_SUDO=yes

COPY . cosim_toolbox/

RUN echo "===== Building CoSim Jupyter =====" && \
  echo "root:worker" | chpasswd && \
  echo "<<<< Adding the 'worker' user >>>>" && \
  useradd -m -s /bin/bash -u $SIM_UID ${COSIM_USER} && \
  echo "<<<< Changing new user password >>>>" && \
  echo "${COSIM_USER}:${COSIM_USER}" | chpasswd && \
  echo "jovyan:worker" | chpasswd && \
  usermod -aG ${COSIM_USER} jovyan && \
  #  usermod -aG sudo ${COSIM_USER} && \   sudo does not work, also the passwords don't work
  #  usermod -aG sudo jovyan && \
  cp /home/jovyan/.bashrc ${COSIM_HOME}/.bashrc && \
  chown -R ${COSIM_USER} ${COSIM_HOME}/.bashrc && \
# Lines below are all for debug
#  echo $(pwd) && \
#  echo  $(ls -las)
  cd cosim_toolbox || exit && \
  pip install --no-cache-dir -e . && \
  chown -R jovyan ../cosim_toolbox

# RUN chown -hR $COSIM_USER:$COSIM_USER $COSIM_HOME
# Copy Binaries
#COPY --from=cosim-build:latest $INSTDIR/ $INSTDIR/
#RUN chown -hR $COSIM_USER:$COSIM_USER $COSIM_HOME

# Set as user
USER jovyan
WORKDIR /home/jovyan

RUN echo "==" && \
  # add the new finger print for each host connection
  mkdir -p .ssh && \
  ssh-keyscan ${SIM_HOST} >> .ssh/known_hosts && \
  ssh-keygen -f copper-key-ecdsa -t ecdsa -b 521
# Line below needs to set at run for right now in the terminal for user:
# ssh-copy-id -i copper-key-ecdsa ${SIM_USER}@${SIM_HOST}

# Set as user
#USER $COSIM_USER
#WORKDIR $COSIM_HOME
