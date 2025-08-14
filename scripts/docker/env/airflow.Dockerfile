# Build runtime image
FROM apache/airflow:2.10.3-python3.12 AS cosim-airflow

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

# Enable to test connection to servers
ENV AIRFLOW__CORE__TEST_CONNECTION=Enabled

COPY . cosim_toolbox/

RUN echo "===== Building CoSimulation Toolbox - Airflow 2.7.3 python 3.10 =====" && \
  pip install --no-cache-dir --upgrade pip && \
  cd cosim_toolbox || exit && \
  pip install --no-cache-dir -e . && \
  mkdir -p /home/airflow/.ssh && \
  touch /home/airflow/.ssh/known_hosts && \
#  ssh-keyscan ${CST_HOST} >> /home/airflow/.ssh/known_hosts && \
  ssh-keygen -f /home/airflow/.ssh/copper-key-ecdsa -t ecdsa -b 521
# Line below needs to set at run for right now in the terminal to copy to 'authorized_keys' to user:
# ssh-copy-id -i /home/airflow/.ssh/copper-key-ecdsa ${LOCAL_USER}@${CST_HOST}
