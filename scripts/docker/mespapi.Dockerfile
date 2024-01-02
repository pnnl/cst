# Build runtime image
FROM mesp-julia:latest AS mesp-mespapi

USER root

# TESP user name and work directory
ENV USER_NAME=worker
ENV USER_HOME=/home/$USER_NAME
ENV TESPDIR=$USER_HOME/tesp
ENV INSTDIR=$TESPDIR/tenv

RUN echo "===== BUILD RUN TESP API =====" && \
  export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  echo "===== Install Libraries =====" && \
  apt-get update && \
  apt-get dist-upgrade -y && \
  apt-get install -y \
  git

# Set 'worker' as user
USER $USER_NAME
WORKDIR $USER_HOME

# Copy Binaries
# COPY --from=tesp-build:latest $INSTDIR/ $INSTDIR/

RUN  echo "Activate the python virtual environment" && \
  . $USER_HOME/venv/bin/activate && \
# Install Python Libraries
  git clone https://devops.pnnl.gov/e-comp/thrust-3/prototype_mesp.git mesp && \
  pip install -r $USER_HOME/mesp/prototype/requirements.txt >> "pypi.log" && \
  julia $USER_HOME/mesp/prototype/install_julia_packages.jl

# This provides the mesp packages without having pip install packages
#PACK=/home/worker/venv/lib/python3.8/site-packages && \
#cat > "$PACK/path.pth" << EOF \
#${MESPDIR}/prototype/src \
#${MESPDIR}/prototype/tests \
#EOF \
