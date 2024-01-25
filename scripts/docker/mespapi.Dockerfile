# Build runtime image
FROM cosim-julia:latest AS cosim-mespapi

USER root

# User name and work directory
ARG UID
ARG COSIM_USER
ENV COSIM_HOME=/home/$COSIM_USER

# Compile exports
ENV MESPDIR=$COSIM_HOME/mesp

RUN echo "===== Building CoSim MESP API =====" && \
  export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  echo "===== Install Libraries =====" && \
  apt-get update && \
  apt-get dist-upgrade -y

COPY . $MESPDIR/
RUN chown -hR $COSIM_USER:$COSIM_USER $COSIM_HOME

# Set user
USER $COSIM_USER
WORKDIR $COSIM_HOME

RUN echo "Install Python Libraries" && \
#  echo "Activate the python virtual environment" && \
#  . venv/bin/activate && \
#  cd $COSIM_HOME/mesp_support/mesp_support || exit && \
#  pip install -e .  >> "pypi.log" && \
  echo "Install Julia Libraries" && \
  julia $MESPDIR/prototype/install_julia_packages.jl

# This provides the mesp packages without having pip install packages
#PACK=/home/worker/venv/lib/python3.8/site-packages && \
#cat > "$PACK/path.pth" << EOF \
#${MESPDIR}/prototype/src \
#${MESPDIR}/prototype/tests \
#EOF \
