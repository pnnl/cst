# Declare arguments
ARG UBUNTU=ubuntu
ARG UBUNTU_VERSION=:20.04

# Build runtime image
FROM ${UBUNTU}${UBUNTU_VERSION} AS cosim-helics

ARG UID
# User name and work directory
ENV USER_NAME=worker
ENV USER_HOME=/home/$USER_NAME
ENV INSTDIR=$USER_HOME/tenv

# Compile exports
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64

# PATH
ENV PATH=$JAVA_HOME:$INSTDIR/bin:$PATH

RUN echo "===== BUILD RUN Helics =====" && \
  export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  echo "===== Install Libraries =====" && \
  apt-get update && \
  apt-get dist-upgrade -y && \
  apt-get install -y \
# Java libraries
  openjdk-11-jdk \
# HELICS and FNCS support libraries
  lsof \
  libzmq5-dev \
  libczmq-dev \
  libboost-dev && \
  ln -s /usr/lib/jvm/java-11-openjdk-amd64 /usr/lib/jvm/default-java && \
  echo "===== Clean Up =====" && \
  apt-get upgrade -y && \
  apt-get clean -y && \
  apt-get autoclean -y && \
  apt-get autoremove -y && \
# protect images by changing root password
  echo "root:worker" | chpasswd && \
  echo "<<<< Adding the 'worker' user >>>>" && \
  useradd -m -s /bin/bash -u $UID ${USER_NAME} && \
  echo "<<<< Changing new user password >>>>" && \
  echo "${USER_NAME}:${USER_NAME}" | chpasswd && \
  usermod -aG sudo ${USER_NAME}

# Set 'worker' as user
USER $USER_NAME
WORKDIR $USER_HOME

# Add directories and files
RUN echo "Directory structure for running" && \
  mkdir -p tenv

# Copy Binaries
COPY --from=cosim-build:latest $INSTDIR/ $INSTDIR/


