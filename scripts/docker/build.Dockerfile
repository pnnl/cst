FROM cosim-library AS cosim-production

# User name and work directory
ARG UID
ARG USER_NAME
ENV USER_HOME=/home/$USER_NAME
ENV USER_EMAIL=pnnl.com

USER $USER_NAME
WORKDIR $USER_HOME

# CoSim exports
ENV INSTDIR=$USER_HOME/tenv
ENV BUILDDIR=$USER_HOME/builder
ENV REPODIR=$USER_HOME/repository

# COMPILE exports
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ENV PYHELICS_INSTALL=$INSTDIR
ENV GLPATH=$INSTDIR/lib/gridlabd:$INSTDIR/share/gridlabd
ENV CPLUS_INCLUDE_PATH=/usr/include/hdf5/serial
ENV FNCS_INCLUDE_DIR=$INSTDIR/include
ENV FNCS_LIBRARY=$INSTDIR/lib
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$INSTDIR/lib
ENV LD_RUN_PATH=$INSTDIR/lib

# PATH
ENV PATH=$JAVA_HOME:$INSTDIR/bin:$PATH
ENV PATH=$PATH:$INSTDIR/energyplus
ENV PATH=$PATH:$INSTDIR/energyplus/PreProcess
ENV PATH=$PATH:$INSTDIR/energyplus/PostProcess

# PSST exports
ENV PSST_SOLVER=cbc
# 'PSST_SOLVER path' -- one of "cbc", "ipopt", "/ibm/cplex/bin/x86-64_linux/cplexamp"
ENV PSST_WARNING=ignore

RUN echo "===== Building CoSim Build =====" && \
  echo "Configure name and email for" && \
  git config --global user.name "${USER_NAME}" && \
  git config --global user.email "${USER_NAME}@${USER_NAME}.com" && \
  echo "User .name=${USER_NAME} and .email=${USER_NAME}@${USER_EMAIL} have been set for git repositories!" && \
  git config --global credential.helper store && \
  echo "Directory structure for build" && \
  mkdir -p tenv && \
  mkdir -p builder && \
  mkdir -p repository

# Copy the build instructions
COPY . ${BUILDDIR}

RUN echo "Cloning or download all relevant repositories..." && \
  cd ${REPODIR} || exit && \
  echo ++++++++++++++ TESP && \
  git clone -b main https://github.com/pnnl/tesp.git && \
#  ${BUILDDIR}/patch.sh tesp tesp && \
  echo "++++++++++++++ PSST" && \
  git clone -b master https://github.com/ames-market/AMES-V5.0.git && \
  echo "Applying the patch for AMES...... from ${BUILDDIR}" && \
  ${BUILDDIR}/patch.sh AMES-V5.0 AMES-V5.0 && \
  echo "++++++++++++++ FNCS" && \
  git clone -b feature/opendss https://github.com/FNCS/fncs.git && \
  ${BUILDDIR}/patch.sh fncs fncs && \
  echo "++++++++++++++ HELICS" && \
  git clone -b main https://github.com/GMLC-TDC/HELICS-src && \
  ${BUILDDIR}/patch.sh HELICS-src HELICS-src && \
  echo "++++++++++++++ GRIDLAB" && \
  git clone -b develop https://github.com/gridlab-d/gridlab-d.git && \
  ${BUILDDIR}/patch.sh gridlab-d gridlab-d && \
  echo "++++++++++++++ ENERGYPLUS" && \
  git clone -b fncs_9.3.0 https://github.com/FNCS/EnergyPlus.git && \
  ${BUILDDIR}/patch.sh EnergyPlus EnergyPlus && \
  echo "++++++++++++++ NS-3" && \
  git clone https://gitlab.com/nsnam/ns-3-dev.git && \
  ${BUILDDIR}/patch.sh ns-3-dev ns-3-dev && \
  echo "++++++++++++++ HELICS-NS-3" && \
  git clone -b main https://github.com/GMLC-TDC/helics-ns3 ns-3-dev/contrib/helics && \
  ${BUILDDIR}/patch.sh ns-3-dev/contrib/helics helics-ns3 && \
  echo "++++++++++++++ KLU SOLVER" && \
  unzip -q ${BUILDDIR}/KLU_DLL.zip -d ./KLU_DLL && \
  echo "++++++++++++++  Compiling and Installing TESP software is starting!  ++++++++++++++" && \
  cd ${BUILDDIR} || exit && \
  echo "Compiling and Installing FNCS..." && \
  ./fncs_b.sh clean > fncs.log 2>&1 && \
  echo "Compiling and Installing FNCS for Java..." && \
  ./fncs_j_b.sh clean > fncs_j.log 2>&1 && \
  /bin/rm -r ${REPODIR}/fncs && \
  echo "Compiling and Installing HELICS..." && \
  ./HELICS-src_b.sh clean > HELICS-src.log 2>&1 && \
  /bin/rm -r ${REPODIR}/HELICS-src && \
  echo "Compiling and Installing KLU..." && \
  ./KLU_DLL_b.sh clean > KLU_DLL.log 2>&1 && \
  /bin/rm -r ${REPODIR}/KLU_DLL && \
  echo "Compiling and Installing Gridlabd..." && \
  ./gridlab-d_b.sh clean > gridlab-d.log 2>&1 && \
  /bin/rm -r ${REPODIR}/gridlab-d && \
  echo "Compiling and Installing EnergyPlus..." && \
  ./EnergyPlus_b.sh clean > EnergyPlus.log 2>&1 && \
  /bin/rm -r ${REPODIR}/EnergyPlus && \
  echo "Compiling and Installing NS-3..." && \
  ./ns-3-dev_b.sh clean > ns-3-dev.log 2>&1 && \
  /bin/rm -r ${REPODIR}/ns-3-dev && \
  echo "Compiling and Installing Ipopt with ASL and Mumps..." && \
  ./ipopt_b.sh clean > ipopt.log 2>&1 && \
  /bin/rm -r ${REPODIR}/Ipopt && \
  /bin/rm -r ${REPODIR}/ThirdParty-ASL && \
  /bin/rm -r ${REPODIR}/ThirdParty-Mumps && \
  echo "Compiling and Installing TESP agents and converter..." && \
  ./tesp_b.sh clean > EnergyPlus_j.log 2>&1 && \
  /bin/rm -r ${REPODIR}/tesp && \
  echo "${USER_NAME}" | sudo -S ldconfig && \
  cd ${BUILDDIR} || exit && \
  ./versions.sh