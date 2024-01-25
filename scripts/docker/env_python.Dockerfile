# Build runtime image
FROM cosim-helics:latest AS cosim-python

USER root

# User name and work directory
ARG UID
ARG COSIM_USER
ENV COSIM_HOME=/home/$COSIM_USER
ARG SIM_USER
ARG SIM_HOST
ENV SIM_USER=$SIM_USER
ENV SIM_HOST=$SIM_HOST

# Compile exports
ENV INSTDIR=$COSIM_HOME/tenv
ENV POSTGRES_HOST="$POSTGRES_HOST"
ENV POSTGRES_DB="$POSTGRES_DB"
ENV POSTGRES_USER="$POSTGRES_USER"
ENV POSTGRES_PASSWORD="$POSTGRES_PASSWORD"
ENV POSTGRES_PORT=$POSTGRES_PORT
ENV MONGO_HOST="$MONGO_HOST"
ENV MONGO_DB="$MONGO_DB"

# PATH
ENV PYHELICS_INSTALL=$INSTDIR

RUN echo "===== Building CoSim Python =====" && \
  export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  echo "===== Install Libraries =====" && \
  apt-get install -y software-properties-common && \
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
  python3-pil.imagetk

# Copy Files
COPY . $COSIM_HOME/cosim_toolbox/cosim_toolbox/
COPY --from=cosim-build:latest $COSIM_HOME/repository/AMES-V5.0/psst/ $COSIM_HOME/psst/psst/
COPY --from=cosim-build:latest $COSIM_HOME/repository/AMES-V5.0/README.rst $COSIM_HOME/psst
RUN chown -hR $COSIM_USER:$COSIM_USER $COSIM_HOME

# Set as user
USER $COSIM_USER
WORKDIR $COSIM_HOME

# Add directories and files
RUN echo "Directory structure for running" && \
  pip install --upgrade pip > "_pypi.log" && \
  pip install virtualenv >> "_pypi.log" && \
  ".local/bin/virtualenv" venv --prompt TESP && \
  echo "Add python virtual environment to .bashrc" && \
  echo ". venv/bin/activate" >> .bashrc && \
  echo "Activate the python virtual environment" && \
  . venv/bin/activate && \
  pip install --upgrade pip > "pypi.log" && \
  echo "Install Python Libraries" && \
  pip install --no-cache-dir helics >> "pypi.log" && \
  pip install --no-cache-dir helics[cli] >> "pypi.log" && \
  cd $COSIM_HOME/cosim_toolbox/cosim_toolbox || exit && \
  pip install --no-cache-dir -e .  >> "$COSIM_HOME/pypi.log" && \
  cd $COSIM_HOME/psst/psst || exit && \
  pip install --no-cache-dir -e .  >> "$COSIM_HOME/pypi.log"
