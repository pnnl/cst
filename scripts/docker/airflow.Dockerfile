FROM apache/airflow:2.7.3 AS cosim-airflow

ENV DOCKER_HOSTS=gage

COPY . cosim_toolbox/

RUN pip install --no-cache-dir -U pip setuptools wheel && \
pip install --no-cache-dir python-dotenv SQLAlchemy && \
cd cosim_toolbox || exit && \
pip3 install --no-cache-dir -e . && \
# add the new finger print for each host connection
mkdir ~/.ssh && \
ssh-keyscan ${DOCKER_HOSTS} >> ~/.ssh/known_hosts && \
ssh-keygen -f ~/copper-key-ecdsa -t ecdsa -b 521
