# Build runtime image
FROM tesp-python:latest AS mesp-julia

USER root

# TESP user name and work directory
ENV USER_NAME=worker
ENV USER_HOME=/home/$USER_NAME
ENV INSTDIR=$TESPDIR/tenv

RUN echo "===== BUILD RUN Julia =====" && \
  export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  echo "===== Install Libraries =====" && \
  apt-get update && \
  apt-get dist-upgrade -y && \
  apt-get install -y \
  git \
  wget

# Set 'worker' as user
USER $USER_NAME
WORKDIR $USER_HOME

RUN echo "Directory structure for running" && \
  wget https://julialang-s3.julialang.org/bin/linux/x64/1.9/julia-1.9.4-linux-x86_64.tar.gz && \
  tar zxvf julia-1.9.4-linux-x86_64.tar.gz  >> "julia.log" && \
  mkdir -p psst/psst

# Copy Binaries
# COPY --from=tesp-build:latest $INSTDIR/ $INSTDIR/
COPY --from=tesp-build:latest $USER_HOME/repository/AMES-V5.0/psst/ $USER_HOME/psst/psst/
COPY --from=tesp-build:latest $USER_HOME/repository/AMES-V5.0/README.rst $USER_HOME/psst

RUN echo "Activate the python virtual environment" && \
  . $USER_HOME/venv/bin/activate && \
  echo "Install Python Libraries" && \
  cd $USER_HOME/psst/psst || exit && \
  pip3 install -e .  >> "pypi.log"

