# Build runtime image
FROM cosim-python:latest AS cosim-julia

USER root

# User name and work directory
ARG UID
ARG USER_NAME
ENV USER_HOME=/home/$USER_NAME

# Compile exports
ENV INSTDIR=$USER_NAME/tenv

# PATH
ENV PATH=$USER_HOME/julia-1.9.4/bin:$PATH

RUN echo "===== Building CoSim Julia =====" && \
  export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  echo "===== Install Libraries =====" && \
  apt-get update && \
  apt-get dist-upgrade -y && \
  apt-get install -y \
  wget && \
  chown -hR $USER_NAME:$USER_NAME $USER_HOME

# Set as user
USER $USER_NAME
WORKDIR $USER_HOME

RUN echo "Directory structure for running" && \
  wget https://julialang-s3.julialang.org/bin/linux/x64/1.9/julia-1.9.4-linux-x86_64.tar.gz && \
  tar zxvf julia-1.9.4-linux-x86_64.tar.gz  >> "julia.log" && \
  rm julia-1.9.4-linux-x86_64.tar.gz
