# Build runtime image
FROM cosim-cst:latest AS cosim-tespapi

USER root

ARG CST_USER
ENV CST_HOME=/home/$CST_USER

# Compile exports

# Copy files

# Set as user
USER $CST_USER
WORKDIR $CST_HOME

# Add directories and files
RUN echo "===== Building CoSimulation Toolbox - TESP =====" && \
  echo "Activate the python virtual environment" && \
  . venv/bin/activate && \
  pip install --no-cache-dir tesp-support >> pypi.log && \
  tesp_component -c 1
