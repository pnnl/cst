# Build runtime image
FROM cosim-helics:latest AS cosim-ns3

USER root

# User name and work directory
ENV USER_NAME=worker
ENV USER_HOME=/home/$USER_NAME
ENV INSTDIR=$USER_HOME/tenv

# PATH
#ENV PATH=$PATH

RUN echo "===== BUILD RUN NS3 =====" && \
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
#COPY --from=cosim-build:latest $INSTDIR/ $INSTDIR/
