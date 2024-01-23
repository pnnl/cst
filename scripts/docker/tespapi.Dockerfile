# Build runtime image
FROM cosim-python:latest AS cosim-tespapi

USER root

# User name and work directory
ARG UID
ARG USER_NAME
ENV USER_HOME=/home/$USER_NAME

RUN echo "===== Building CoSim TESP API =====" && \
  export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  echo "===== Install Libraries =====" && \
  apt-get update && \
  apt-get dist-upgrade -y && \
  apt-get install -y \
  git

# Copy Binaries
#COPY --from=cosim-build:latest $INSTDIR/ $INSTDIR/
#RUN chown -hR $USER_NAME:$USER_NAME $USER_HOME

# Set as user
USER $USER_NAME
WORKDIR $USER_HOME

# Add directories and files
RUN echo "Install Python Libraries" && \
  echo "Activate the python virtual environment" && \
  . venv/bin/activate && \
  pip install --no-cache-dir tesp-support >> pypi.log && \
  tesp_component -c 1
