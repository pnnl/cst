# Build runtime image
FROM cosim-python:latest AS cosim-tespapi

USER root

# User name and work directory
ENV USER_NAME=worker
ENV USER_HOME=/home/$USER_NAME

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

# Add directories and files
RUN echo "Install Python Libraries" && \
  echo "Activate the python virtual environment" && \
  . venv/bin/activate && \
  pip install tesp-support >> pypi.log && \
  tesp_component -c 1
