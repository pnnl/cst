ENV DOCKER_HOSTS=boomer gage maxwell

FROM apache/airflow:2.2.3
ADD requirements.txt /usr/local/airflow/requirements.txt
RUN pip install --no-cache-dir -U pip setuptools wheel && \
pip install --no-cache-dir -r /usr/local/airflow/requirements.txt && \
# add the new finger print for each host connection
mkdir ~/.ssh && \
ssh-keyscan ${DOCKER_HOSTS} >> ~/.ssh/known_hosts && \
ssh-keygen -f ~/copper-key-ecdsa -t ecdsa -b 521

