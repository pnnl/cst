# Build runtime image
FROM cosim-python:latest AS cosim-julia

USER root

# User name and work directory
ARG UID
ARG COSIM_USER
ENV COSIM_HOME=/home/$COSIM_USER

# Compile exports
ENV INSTDIR=$COSIM_USER/tenv

# PATH
ENV PATH=$COSIM_HOME/julia-1.9.4/bin:$PATH

RUN echo "===== Building CoSim Julia =====" && \
  export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  echo "===== Install Libraries =====" && \
  apt-get update && \
  apt-get dist-upgrade -y && \
  apt-get install -y \
  wget && \
  chown -hR $COSIM_USER:$COSIM_USER $COSIM_HOME

# Set as user
USER $COSIM_USER
WORKDIR $COSIM_HOME

RUN echo "Directory structure for running" && \
  wget https://julialang-s3.julialang.org/bin/linux/x64/1.9/julia-1.9.4-linux-x86_64.tar.gz && \
  tar zxvf julia-1.9.4-linux-x86_64.tar.gz  >> "julia.log" && \
  rm julia-1.9.4-linux-x86_64.tar.gz
