# Build runtime image
FROM cosim-ubuntu:latest AS cosim-gridlabd

ARG CST_GRP
ARG CST_USER
ARG OPT_HOME=/opt

# CoSimulation Toolbox exports
ENV INSTDIR=$OPT_HOME/tenv
ENV REPO_DIR=$OPT_HOME/repo
ENV BUILD_DIR=$OPT_HOME/build

# COMPILE exports
ENV PYHELICS_INSTALL=$INSTDIR
ENV GLPATH=$INSTDIR/lib/gridlabd:$INSTDIR/share/gridlabd
ENV CPLUS_INCLUDE_PATH=/usr/include/hdf5/serial:$INSTDIR/include
ENV LD_LIBRARY_PATH=$INSTDIR/lib
ENV LD_RUN_PATH=$INSTDIR/lib
ENV HELICS_DIR=/usr/local/lib/python3.12/dist-packages/helics/install/lib64/cmake/HELICS

# PATH
ENV PATH=$INSTDIR/bin:$OPT_HOME/.local/bin:$PATH

COPY . ${BUILD_DIR}

RUN echo "===== Building CoSimulation Toolbox - GridlabD Docker =====" && \
  export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  apt-get update && \
  apt-get dist-upgrade -y && \
  apt-get install -y \
  git \
  wget \
  unzip \
  pkgconf \
  build-essential \
  autoconf \
  libtool \
  gfortran \
  cmake \
  libboost-dev \
  libjsoncpp-dev \
  libxerces-c-dev \
  libsuitesparse-dev \
  libhdf5-serial-dev && \
  echo "Directory structure for build" && \
  cd opt || exit && \
  mkdir -p tenv && \
  mkdir -p repo && \
  echo "Cloning or download all relevant repositories..." && \
  cd ${REPO_DIR} || exit && \
  echo "++++++++++++++ GRIDLAB" && \
  git clone -b develop https://github.com/gridlab-d/gridlab-d.git && \
  ${BUILD_DIR}/patch.sh gridlab-d gridlab-d && \
  echo "++++++++++++++ KLU SOLVER" && \
  unzip -q ${BUILD_DIR}/KLU_DLL.zip -d ./KLU_DLL && \
  echo "++++++++++++++  Compiling and Installing grid software is starting!  ++++++++++++++" && \
  cd ${BUILD_DIR} || exit && \
  echo "Compiling and Installing KLU..." && \
  ./KLU_DLL_b.sh clean > KLU_DLL.log 2>&1 && \
  echo "Compiling and Installing Gridlabd..." && \
  ./gridlab-d_b.sh clean > gridlab-d.log 2>&1 && \
  cd .. | exit && \
  echo "Remove all repositories..." && \
  rm -r ${REPO_DIR} && \
  rm -r ${BUILD_DIR} && \
  echo "Remove all build tools..." && \
  apt-get remove -y \
  git \
  wget \
  unzip \
  pkgconf \
  build-essential \
  autoconf \
  libtool \
  gfortran \
  cmake && \
  apt-get autoremove -y && \
  export REPO_DIR= && \
  export BUILD_DIR= && \
#  rm -rf /var/lib/apt/lists/* && \
  gridlabd --version && \
  chown -hR $CST_USER:$CST_GRP $CST_HOME

# Set as user
USER $CST_USER
WORKDIR /home/$CST_USER