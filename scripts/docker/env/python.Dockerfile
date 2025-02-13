# Build runtime image
FROM cosim-helics:latest AS cosim-python

ARG CST_GID
ARG CST_GRP

USER root

ENV LOCAL_UID=$LOCAL_UID
ENV LOCAL_USER=$LOCAL_USER

ENV CST_HOST="$CST_HOST"
ENV CST_WSL_HOST=$CST_WSL_HOST
ENV CST_WSL_PORT=$CST_WSL_PORT

ENV CST_UID=$CST_UID
ENV CST_USER=$CST_USER
ENV CST_PASSWORD=$CST_PASSWORD
ENV CST_HOME=$CST_HOME
ENV CST_ROOT=$CST_ROOT
ENV CST_DB=$CST_DB

ENV POSTGRES_HOST="$CST_HOST"
ENV POSTGRES_PORT=$POSTGRES_PORT
ENV MONGO_HOST="$MONGO_HOST"
ENV MONGO_PORT=$MONGO_PORT

# Copy Files
COPY . $CST_HOME/cosim_toolbox/cosim_toolbox/
#COPY --from=cosim-build:latest $CST_HOME/repo/psst/ $CST_HOME/psst/psst/
#COPY --from=cosim-build:latest $CST_HOME/repo/README.rst $CST_HOME/psst
RUN chown -hR $CST_USER:$CST_GRP $CST_HOME

# Set as user
USER $CST_USER
WORKDIR $CST_HOME

# Add directories and files
RUN echo "===== Building CoSimulation Toolbox - Python =====" && \
  pip install --upgrade pip > "_pypi.log" && \
#  pip install --no-cache-dir helics >> "pypi.log" && \
#  pip install --no-cache-dir helics[cli] >> "pypi.log" && \
  cd $CST_HOME/cosim_toolbox/cosim_toolbox || exit && \
  pip install --no-cache-dir -e .  >> "$CST_HOME/pypi.log"
#    && \
#  cd $CST_HOME/psst/psst || exit && \
#  pip install --no-cache-dir -e .  >> "$CST_HOME/pypi.log"
