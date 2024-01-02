# Build runtime image
FROM tesp-python:latest AS tesp-tespapi

USER root

# TESP user name and work directory
ENV USER_NAME=worker
ENV USER_HOME=/home/$USER_NAME
ENV INSTDIR=$USER_HOME/tenv

RUN echo "===== BUILD RUN TESP API =====" && \
  export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  echo "===== Install Libraries =====" && \
  apt-get update && \
  apt-get dist-upgrade -y && \
  apt-get install -y \
  git

# Set 'worker' as user
USER $USER_NAME
WORKDIR $USER_HOME

RUN echo "Directory structure for running" && \
  mkdir -p psst/psst

# Copy Binaries
# COPY --from=tesp-build:latest $INSTDIR/ $INSTDIR/
COPY --from=tesp-build:latest $USER_HOME/repository/AMES-V5.0/psst/ $USER_HOME/psst/psst/
COPY --from=tesp-build:latest $USER_HOME/repository/AMES-V5.0/README.rst $USER_HOME/psst

# Add directories and files
RUN echo "Activate the python virtual environment" && \
  . $USER_HOME/venv/bin/activate && \
  echo "Install Python Libraries" && \
  pip3 install tesp-support  >> "pypi.log"&& \
  cd $USER_HOME/psst/psst || exit && \
  pip3 install -e .  >> "pypi.log" && \
  tesp_component -c 1
