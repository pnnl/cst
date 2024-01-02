# Build runtime image
FROM tesp-helics:latest AS tesp-run

USER root

# User name and work directory
ENV USER_NAME=worker
ENV USER_HOME=/home/$USER_NAME
ENV INSTDIR=$USER_HOME/tenv

# PATH
ENV PATH=$PATH:$INSTDIR/energyplus
ENV PATH=$PATH:$INSTDIR/energyplus/PreProcess
ENV PATH=$PATH:$INSTDIR/energyplus/PostProcess
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$INSTDIR/lib

RUN echo "===== BUILD RUN EnergyPlus =====" && \
  export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  echo "===== Install Libraries =====" && \
  apt-get update && \
  apt-get dist-upgrade -y

# Set 'worker' as user
USER $USER_NAME
WORKDIR $USER_HOME

# Add directories and files
#RUN echo "Directory structure for running" && \
#  mkdir -p tenv

# Copy Binaries
#COPY --from=tesp-build:latest $INSTDIR/ $INSTDIR/
