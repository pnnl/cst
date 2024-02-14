# Build runtime image
FROM apache/airflow:2.7.3 AS cosim-airflow

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

# Enable to test connection to servers
ENV AIRFLOW__CORE__TEST_CONNECTION=Enabled

COPY . cosim_toolbox/

RUN echo "===== Building CoSim Airflow =====" && \
  pip install --no-cache-dir --upgrade pip && \
  cd cosim_toolbox || exit && \
  pip install --no-cache-dir -e .
  mkdir -p .ssh && \
  touch .ssh/known_hosts && \
#  ssh-keyscan ${SIM_HOST} >> .ssh/known_hosts && \
  ssh-keygen -f copper-key-ecdsa -t ecdsa -b 521
# Line below needs to set at run for right now in the terminal to copy to 'authorized_keys' to user:
# ssh-copy-id -i copper-key-ecdsa ${SIM_USER}@${SIM_HOST}
