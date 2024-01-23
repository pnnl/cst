# Build runtime image
FROM jupyter/minimal-notebook:7285848c0a11

USER root

# User name and work directory
ARG UID
ARG USER_NAME
ENV USER_HOME=/home/$USER_NAME

ENV GRANT_SUDO=yes

ARG DOCKER_USER=d3j331
ARG DOCKER_HOST=gage.pnl.gov

COPY . cosim_toolbox/

RUN echo "===== Building CoSim Jupyter =====" && \
  echo "root:worker" | chpasswd && \
  echo "<<<< Adding the 'worker' user >>>>" && \
  useradd -m -s /bin/bash -u $UID ${USER_NAME} && \
  echo "<<<< Changing new user password >>>>" && \
  echo "${USER_NAME}:${USER_NAME}" | chpasswd && \
  echo "jovyan:worker" | chpasswd && \
  usermod -aG ${USER_NAME} jovyan && \
  #  usermod -aG sudo ${USER_NAME} && \   sudo does not work, also the passwords don't work
  #  usermod -aG sudo jovyan && \
  cp /home/jovyan/.bashrc ${USER_HOME}/.bashrc && \
  chown -R ${USER_NAME} ${USER_HOME}/.bashrc && \
# Lines below are all for debug
#  echo $(pwd) && \
#  echo  $(ls -las)
  cd cosim_toolbox || exit && \
  pip install --no-cache-dir -e . && \
  chown -R jovyan ../cosim_toolbox

# RUN chown -hR $USER_NAME:$USER_NAME $USER_HOME
# Copy Binaries
#COPY --from=cosim-build:latest $INSTDIR/ $INSTDIR/
#RUN chown -hR $USER_NAME:$USER_NAME $USER_HOME

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
#USER $USER_NAME
#WORKDIR $USER_HOME
