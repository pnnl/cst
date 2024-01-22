FROM apache/airflow:2.7.3 AS cosim-airflow

ENV DOCKER_HOST=gage.pnl.gov
# Enable to test connection to servers
ENV AIRFLOW__CORE__TEST_CONNECTION=Enabled

COPY . cosim_toolbox/

RUN echo "===== Building CoSim Airflow =====" && \
  pip install --no-cache-dir --upgrade pip && \
  pip install --no-cache-dir python-dotenv SQLAlchemy && \
  cd cosim_toolbox || exit && \
  pip3 install --no-cache-dir -e .
