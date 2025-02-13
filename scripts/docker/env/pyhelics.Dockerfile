# Build runtime image
FROM python:3.10-bookworm AS cosim-helics

ARG CST_GID
ARG CST_GRP

# User name and work directory
ENV LOCAL_UID=$LOCAL_UID
ENV LOCAL_USER=$LOCAL_USER

ENV CST_HOST="$CST_HOST"
ENV CST_WSL_HOST=$CST_WSL_HOST
ENV CST_WSL_PORT=$CST_WSL_PORT

ENV CST_UID=$CST_UID
ENV CST_USER="$CST_USER"
ENV CST_PASSWORD="$CST_PASSWORD"
ENV CST_HOME=$CST_HOME
ENV CST_ROOT=$CST_ROOT
ENV CST_DB="$CST_DB"

ENV POSTGRES_HOST="$CST_HOST"
ENV POSTGRES_PORT=$POSTGRES_PORT
ENV MONGO_HOST="$MONGO_HOST"
ENV MONGO_PORT=$MONGO_PORT

ENV CST_HOME=/home/$CST_USER
ENV INSTDIR=$CST_HOME/tenv

# PATH
ENV PATH=$CST_HOME/tenv/bin:$PATH

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
ENV PATH=$CST_HOME/tenv/ibm/cplex/bin/x86-64_linux:$CST_HOME/tenv/bin:$PATH
ENV PSST_SOLVER=$CST_HOME/tenv/ibm/cplex/bin/x86-64_linux/cplexamp

COPY "./cplex_studio129.linux-x86-64.bin" .
RUN echo "===== Installing CPlex =====" && \
    chmod a+x "cplex_studio129.linux-x86-64.bin" && \
    "./cplex_studio129.linux-x86-64.bin" -i silent -DLICENSE_ACCEPTED=TRUE -DUSER_INSTALL_DIR=$CST_HOME/tenv/ibm && \
    rm "cplex_studio129.linux-x86-64.bin" && \
    chown -hR $CST_USER:$CST_GRP $CST_HOME

# Set as user
USER $CST_USER
WORKDIR $CST_HOME

RUN echo "===== Building CoSimulation Toolbox - Python =====" && \
  pip install --upgrade pip > "_pypi.log" && \
  pip install --no-cache-dir helics >> "pypi.log" && \
  pip install --no-cache-dir helics[cli] >> "pypi.log"