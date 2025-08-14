# Build runtime image
FROM cosim-ubuntu:latest AS cosim-helics

# User name and work directory
ARG CST_GID
ARG CST_GRP
ARG CST_USER
ENV CST_HOME=/home/$CST_USER
ENV INSTDIR=$CST_HOME/tenv

# Compile exports
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ENV PYHELICS_INSTALL=$INSTDIR
ENV GLPATH=$INSTDIR/lib/gridlabd:$INSTDIR/share/gridlabd
# ENV CPLUS_INCLUDE_PATH=/usr/include/hdf5/serial:$INSTDIR/include
# ENV FNCS_INCLUDE_DIR=$INSTDIR/include
# ENV FNCS_LIBRARY=$INSTDIR/lib
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$INSTDIR/lib
# ENV LD_RUN_PATH=$INSTDIR/lib

# PATH
ENV PATH=$JAVA_HOME:$INSTDIR/bin:$PATH
ENV PATH=$PATH:$INSTDIR/energyplus
ENV PATH=$PATH:$INSTDIR/energyplus/PreProcess
ENV PATH=$PATH:$INSTDIR/energyplus/PostProcess

RUN echo "===== Building CoSimulation Toolbox - HELICS =====" && \
  export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  apt-get update && \
  apt-get dist-upgrade -y && \
  echo "root:${CST_USER}" | chpasswd && \
  addgroup --gid ${CST_GID} ${CST_GRP} && \
  useradd -m -s /bin/bash -g ${CST_GRP} -G sudo,${CST_GRP} -u $CST_UID ${CST_USER} && \
  echo "${CST_USER}:${CST_USER}" | chpasswd

#Add cplex
ARG CPLEX_BIN=cplex_studio129.linux-x86-64.bin
ENV PSST_SOLVER=$INSTDIR/ibm/cplex/bin/x86-64_linux/cplexamp
ENV PATH=$INSTDIR/ibm/cplex/bin/x86-64_linux:$PATH

COPY "./$CPLEX_BIN" /opt/
RUN cd /opt && \
    chmod a+x "$CPLEX_BIN" && \
    "./$CPLEX_BIN" -i silent -DLICENSE_ACCEPTED=TRUE -DUSER_INSTALL_DIR=$INSTDIR/ibm && \
    rm "/opt/$CPLEX_BIN"

# Copy Binaries
COPY --from=cosim-build:latest $INSTDIR/ $INSTDIR/
RUN chown -hR $CST_USER:$CST_GRP $CST_HOME

# Set as user
USER $CST_USER
WORKDIR $CST_HOME
