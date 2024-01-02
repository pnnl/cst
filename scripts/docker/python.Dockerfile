# Build runtime image
FROM tesp-helics:latest AS tesp-python

USER root

# User name and work directory
ENV USER_NAME=worker
ENV USER_HOME=/home/$USER_NAME
ENV INSTDIR=$USER_HOME/tenv

# PATH
ENV PYHELICS_INSTALL=$INSTDIR

RUN echo "===== BUILD RUN Python =====" && \
  export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  echo "===== Install Libraries =====" && \
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
  python3-tk \
  python3-pil.imagetk

# Set 'worker' as user
USER $USER_NAME
WORKDIR $USER_HOME

# Add directories and files
RUN echo "Directory structure for running" && \
  pip3 install --upgrade pip > "_pypi.log" && \
  pip3 install virtualenv >> "_pypi.log" && \
  "$USER_HOME/.local/bin/virtualenv" venv --prompt TESP && \
  echo "Activate the python virtual environment" && \
  . $USER_HOME/venv/bin/activate && \
  pip3 install --upgrade pip > "pypi.log" && \
  pip3 install helics >> "pypi.log" && \
  pip3 install helics[cli] >> "pypi.log"

# Copy Binaries
#COPY --from=tesp-build:latest $INSTDIR/ $INSTDIR/
