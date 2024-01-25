# Build runtime image
FROM cosim-helics:latest AS cosim-gridlabd

USER root

# User name and work directory
ARG UID
ARG COSIM_USER
ENV COSIM_HOME=/home/$COSIM_USER

# Compile exports
ENV INSTDIR=$COSIM_HOME/tenv

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

# Copy Binaries
#COPY --from=cosim-build:latest $INSTDIR/ $INSTDIR/
#RUN chown -hR $COSIM_USER:$COSIM_USER $COSIM_HOME

# Set as user
USER $COSIM_USER
WORKDIR $COSIM_HOME
