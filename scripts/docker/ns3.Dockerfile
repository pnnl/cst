# Build runtime image
FROM cosim-helics:latest AS cosim-ns3

USER root

# User name and work directory
ARG UID
ARG COSIM_USER
ENV COSIM_HOME=/home/$COSIM_USER

# Compile exports
ENV INSTDIR=$COSIM_HOME/tenv

# PATH
#ENV PATH=$PATH

RUN echo "===== BUILD RUN NS3 =====" && \
  export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  echo "===== Install Libraries =====" && \
  apt-get update && \
  apt-get dist-upgrade -y

# Copy Binaries
#COPY --from=cosim-build:latest $INSTDIR/ $INSTDIR/
#RUN chown -hR $COSIM_USER:$COSIM_USER $COSIM_HOME

# Set as user
USER $COSIM_USER
WORKDIR $COSIM_HOME
