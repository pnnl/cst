FROM apache/airflow:2.7.3 AS cosim-airflow

ARG SIM_USER
ARG SIM_HOST
ENV SIM_USER=$SIM_USER
ENV SIM_HOST=$SIM_HOST

# Compile exports
ENV POSTGRES_HOST="$SIM_HOST"
ENV POSTGRES_DB="$POSTGRES_DB"
ENV POSTGRES_USER="$POSTGRES_USER"
ENV POSTGRES_PASSWORD="$POSTGRES_PASSWORD"
ENV POSTGRES_PORT=$POSTGRES_PORT
ENV MONGO_HOST="$MONGO_HOST"
ENV MONGO_DB="$MONGO_DB"

# Enable to test connection to servers
ENV AIRFLOW__CORE__TEST_CONNECTION=Enabled

COPY . cosim_toolbox/

RUN echo "===== Building CoSim Airflow =====" && \
  pip install --no-cache-dir --upgrade pip && \
  cd cosim_toolbox || exit && \
  pip install --no-cache-dir -e .
