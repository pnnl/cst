# Declare arguments
ARG UBUNTU=ubuntu
ARG UBUNTU_VERSION=:22.04

# Build runtime image
FROM ${UBUNTU}${UBUNTU_VERSION} AS cosim-fncs

# User name and work directory
ARG UID
ARG USER_NAME
ENV USER_HOME=/home/$USER_NAME

# Compile exports
ENV INSTDIR=$USER_HOME/tenv
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ENV PYHELICS_INSTALL=$INSTDIR

# PATH
ENV PATH=$JAVA_HOME:$INSTDIR/bin:$PATH

RUN echo "===== Building CoSim FNCS =====" && \
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
# protect images by changing root password
  echo "root:worker" | chpasswd && \
  echo "<<<< Adding the 'worker' user >>>>" && \
  useradd -m -s /bin/bash -u $UID ${USER_NAME} && \
  echo "<<<< Changing new user password >>>>" && \
  echo "${USER_NAME}:${USER_NAME}" | chpasswd && \
  usermod -aG sudo ${USER_NAME}

# Copy Binaries
COPY --from=cosim-build:latest $INSTDIR/ $INSTDIR/
RUN chown -hR $USER_NAME:$USER_NAME $USER_HOME

# Set as user
USER $USER_NAME
WORKDIR $USER_HOME
