# Build runtime image
FROM cosim-julia:latest AS cosim-mespapi

USER root

ARG COSIM_USER
ENV COSIM_HOME=/home/$COSIM_USER

# Compile exports
ENV MESPDIR=$COSIM_HOME/mesp

# Copy files
COPY . $MESPDIR/

# Set as user
USER $COSIM_USER
WORKDIR $COSIM_HOME

# Add directories and files
RUN echo "Building Cosim MESP api" && \
  echo "Activate the python virtual environment" && \
  . venv/bin/activate && \
#  cd $COSIM_HOME/mesp_support/mesp_support || exit && \
#  pip install -e .  >> "pypi.log" && \
#  echo "Install Julia Libraries" && \
#  julia $MESPDIR/prototype/install_julia_packages.jl

# This provides the mesp packages without having pip install packages
#PACK=/home/worker/venv/lib/python3.#/site-packages && \
#cat > "$PACK/path.pth" << EOF \
#${MESPDIR}/prototype/src \
#${MESPDIR}/prototype/tests \
#EOF \
