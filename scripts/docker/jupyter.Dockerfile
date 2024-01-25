# Build runtime image
FROM jupyter/minimal-notebook:7285848c0a11

USER root

# User name and work directory
ARG UID
ARG COSIM_USER
ENV COSIM_HOME=/home/$COSIM_USER

ENV GRANT_SUDO=yes

ARG DOCKER_USER=d3j331
ARG DOCKER_HOST=gage.pnl.gov

COPY . cosim_toolbox/

RUN echo "===== Building CoSim Jupyter =====" && \
  echo "root:worker" | chpasswd && \
  echo "<<<< Adding the 'worker' user >>>>" && \
  useradd -m -s /bin/bash -u $UID ${COSIM_USER} && \
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
  ssh-keyscan ${DOCKER_HOST} >> .ssh/known_hosts && \
  ssh-keygen -f copper-key-ecdsa -t ecdsa -b 521
# Line below needs to set at run for right now in the terminal for user:
# ssh-copy-id -i copper-key-ecdsa ${DOCKER_USER}@${DOCKER_HOST}

# Set as user
#USER $COSIM_USER
#WORKDIR $COSIM_HOME
