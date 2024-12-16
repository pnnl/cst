
FROM cosim-helics:latest AS cosim-gridlabd

USER root

ENV SIM_USER=gray570
ENV SIM_HOST=ecomp-thrust-3-sandbox
ENV SIM_WSL_HOST=
ENV SIM_WSL_PORT=
ENV SIM_DIR=/home/gray570/workspace/copper

ENV COSIM_DB="copper"
ENV COSIM_USER="worker"
ENV COSIM_PASSWORD="worker"
ENV COSIM_HOME=/home/worker

ENV POSTGRES_HOST="ecomp-thrust-3-sandbox"
ENV POSTGRES_PORT=5432
ENV MONGO_HOST="mongodb://ecomp-thrust-3-sandbox"
ENV MONGO_PORT=27017

# Copy Files
COPY . /home/worker/cosim_toolbox/cosim_toolbox/
RUN chown -hR worker:worker /home/worker


# Set as user
USER worker
WORKDIR /home/worker