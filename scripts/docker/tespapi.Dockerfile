# Build runtime image
FROM cosim-python:latest AS cosim-tespapi

USER root

ARG COSIM_USER
ENV COSIM_HOME=/home/$COSIM_USER

# Copy Binaries
#COPY --from=cosim-build:latest $INSTDIR/ $INSTDIR/
#RUN chown -hR $COSIM_USER:$COSIM_USER $COSIM_HOME

# Set as user
USER $COSIM_USER
WORKDIR $COSIM_HOME

# Add directories and files
RUN echo "Install Python Libraries" && \
  echo "Activate the python virtual environment" && \
  . venv/bin/activate && \
  pip install --no-cache-dir tesp-support >> pypi.log && \
  tesp_component -c 1
