# Build runtime image
FROM cosim-ubuntu:latest AS cosim-cst

ARG CST_USER

# Copy Files
#COPY --from=cosim-build:latest /home/worker/repo/psst/ /home/worker/psst/psst/
#COPY --from=cosim-build:latest /home/worker/repo/README.rst /home/worker/psst

RUN echo "===== Building CoSimulation Toolbox - CST Docker =====" && \
  rm -rf /var/lib/apt/lists/*

# Set as user
USER $CST_USER
WORKDIR /home/$CST_USER