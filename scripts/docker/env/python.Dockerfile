# Build runtime image
FROM cosim-helics:latest AS cosim-python

USER root

ENV SIM_USER=$SIM_USER
ENV SIM_HOST=$SIM_HOST
ENV SIM_WSL_HOST=$SIM_WSL_HOST
ENV SIM_WSL_PORT=$SIM_WSL_PORT
ENV SIM_DIR=$SIM_DIR

ENV COSIM_DB="$COSIM_DB"
ENV COSIM_USER="$COSIM_USER"
ENV COSIM_PASSWORD="$COSIM_PASSWORD"
ENV COSIM_HOME=$COSIM_HOME

ENV POSTGRES_HOST="$SIM_HOST"
ENV POSTGRES_PORT=$POSTGRES_PORT
ENV MONGO_HOST="$MONGO_HOST"
ENV MONGO_PORT=$MONGO_PORT

# Copy Files
COPY . $COSIM_HOME/cosim_toolbox/cosim_toolbox/
COPY --from=cosim-build:latest $COSIM_HOME/repo/pyhelics/ $COSIM_HOME/pyhelics/
COPY --from=cosim-build:latest $COSIM_HOME/repo/AMES-V5.0/psst/ $COSIM_HOME/psst/psst/
COPY --from=cosim-build:latest $COSIM_HOME/repo/AMES-V5.0/README.rst $COSIM_HOME/psst
RUN chown -hR $COSIM_USER:$COSIM_USER $COSIM_HOME

# Set as user
USER $COSIM_USER
WORKDIR $COSIM_HOME

# Add directories and files
RUN echo "===== Building CoSim Python =====" && \
  echo "Pip install for virtual environment" && \
  pip install --upgrade pip > "_pypi.log" && \
  pip install virtualenv >> "_pypi.log" && \
  ".local/bin/virtualenv" venv --prompt TESP && \
  echo "Add python virtual environment to .bashrc" && \
  echo ". venv/bin/activate" >> .bashrc && \
  echo "Activate the python virtual environment" && \
  . venv/bin/activate && \
  pip install --upgrade pip > "$COSIM_HOME/pypi.log" && \
  echo "Install Python Libraries" && \
  cd /home/worker/pyhelics || exit && \
  pip install --no-cache-dir "." && \
  rm -r /home/worker/pyhelics && \
#  pip install --no-cache-dir helics[cli] >> "$COSIM_HOME/pypi.log" && \
  cd $COSIM_HOME/cosim_toolbox/cosim_toolbox || exit && \
  pip install --no-cache-dir "." && \
  rm -r /home/worker/cosim_toolbox && \
  cd $COSIM_HOME/psst/psst || exit && \
  pip install --no-cache-dir "." && \
  rm -r /home/worker/psst