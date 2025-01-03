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
COPY --from=cosim-build:latest $COSIM_HOME/repo/psst/ $COSIM_HOME/psst/psst/
COPY --from=cosim-build:latest $COSIM_HOME/repo/README.rst $COSIM_HOME/psst
RUN chown -hR $COSIM_USER $COSIM_HOME

# Set as user
USER $COSIM_USER
WORKDIR $COSIM_HOME

# Add directories and files
RUN echo "===== Building CoSim Python =====" && \
  pip install --upgrade pip > "_pypi.log" && \
  pip install --no-cache-dir helics >> "pypi.log" && \
  pip install --no-cache-dir helics[cli] >> "pypi.log" && \
  cd $COSIM_HOME/cosim_toolbox/cosim_toolbox || exit && \
  pip install --no-cache-dir -e .  >> "$COSIM_HOME/pypi.log" && \
  cd $COSIM_HOME/psst/psst || exit && \
  pip install --no-cache-dir -e .  >> "$COSIM_HOME/pypi.log"
