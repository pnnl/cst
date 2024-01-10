# Build runtime image
FROM cosim-helics:latest AS cosim-python

USER root

# User name and work directory
ENV USER_NAME=worker
ENV USER_HOME=/home/$USER_NAME
ENV INSTDIR=$USER_HOME/tenv

# PATH
ENV PYHELICS_INSTALL=$INSTDIR

COPY . $USER_HOME/cosim_toolbox/cosim_toolbox/
COPY --from=cosim-build:latest $USER_HOME/repository/AMES-V5.0/psst/ $USER_HOME/psst/psst/
COPY --from=cosim-build:latest $USER_HOME/repository/AMES-V5.0/README.rst $USER_HOME/psst

RUN echo "===== Building CoSim Python =====" && \
  export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  echo "===== Install Libraries =====" && \
  apt-get install software-properties-common && \
  add-apt-repository ppa:deadsnakes/ppa -y && \
  apt-get update && \
  apt-get dist-upgrade -y && \
  apt-get install -y \
# Ipopt cbc solver support libraries
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
  chown -hR $USER_NAME:$USER_NAME $USER_HOME

# Set 'worker' as user
USER $USER_NAME
WORKDIR $USER_HOME

# Add directories and files
RUN echo "Directory structure for running" && \
  pip3 install --upgrade pip > "_pypi.log" && \
  pip3 install virtualenv >> "_pypi.log" && \
  ".local/bin/virtualenv" venv --prompt TESP && \
  echo "Add python virtual environment to .bashrc" && \
  echo ". venv/bin/activate" >> .bashrc && \
  echo "Activate the python virtual environment" && \
  . venv/bin/activate && \
  pip3 install --upgrade pip > "pypi.log" && \
  echo "Install Python Libraries" && \
  pip3 install --no-cache-dir helics >> "pypi.log" && \
  pip3 install --no-cache-dir helics[cli] >> "pypi.log" && \
  cd $USER_HOME/cosim_toolbox/cosim_toolbox || exit && \
  pip3 install --no-cache-dir -e .  >> "pypi.log" && \
  cd $USER_HOME/psst/psst || exit && \
  pip3 install --no-cache-dir -e .  >> "pypi.log"
