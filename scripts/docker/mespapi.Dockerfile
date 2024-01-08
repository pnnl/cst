# Build runtime image
FROM cosim-julia:latest AS cosim-mespapi

USER root

# User name and work directory
ENV USER_NAME=worker
ENV USER_HOME=/home/$USER_NAME
ENV MESPDIR=$USER_HOME/mesp

COPY . $MESPDIR/

RUN echo "===== BUILD RUN MESP API =====" && \
  export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  echo "===== Install Libraries =====" && \
  apt-get update && \
  apt-get dist-upgrade -y && \
  apt-get install -y && \
  chown -hR $USER_NAME:$USER_NAME $USER_HOME

# Set 'worker' as user
USER $USER_NAME
WORKDIR $USER_HOME

RUN echo "Install Python Libraries" && \
#  echo "Activate the python virtual environment" && \
#  . venv/bin/activate && \
#  cd $USER_HOME/mesp_support/mesp_support || exit && \
#  pip3 install -e .  >> "pypi.log" && \
  echo "Install Julia Libraries" && \
  julia $MESPDIR/prototype/install_julia_packages.jl

# This provides the mesp packages without having pip install packages
#PACK=/home/worker/venv/lib/python3.8/site-packages && \
#cat > "$PACK/path.pth" << EOF \
#${MESPDIR}/prototype/src \
#${MESPDIR}/prototype/tests \
#EOF \
