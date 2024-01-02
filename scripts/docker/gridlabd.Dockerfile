# Build runtime image
FROM tesp-helics:latest AS tesp-gridlabd

USER root

# User name and work directory
ENV USER_NAME=worker
ENV USER_HOME=/home/$USER_NAME
ENV INSTDIR=$USER_HOME/tenv

# Compile exports
ENV GLPATH=$INSTDIR/lib/gridlabd:$INSTDIR/share/gridlabd

RUN echo "===== BUILD RUN Gridlab-D =====" && \
  export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  echo "===== Install Libraries =====" && \
  apt-get update && \
  apt-get dist-upgrade -y && \
  apt-get install -y \
# GridLAB-D support libraries
  libxerces-c-dev \
  libhdf5-serial-dev \
  libsuitesparse-dev

# Set 'worker' as user
USER $USER_NAME
WORKDIR $USER_HOME

# Add directories and files
#RUN echo "Directory structure for running" && \
#  mkdir -p tenv

# Copy Binaries
#COPY --from=tesp-build:latest $INSTDIR/ $INSTDIR/
