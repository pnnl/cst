
FROM cosim-helics:latest AS cosim-gridlabd

ARG CST_GID
ARG CST_GRP

USER root

# Copy Files
COPY . $CST_HOME/cosim_toolbox/cosim_toolbox/
RUN chown -hR $CST_USER:$CST_GRP $CST_HOME

# Set as user
USER worker
WORKDIR /home/worker