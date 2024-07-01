# Build runtime image
FROM cosim-python:latest AS cosim-julia

USER root

ARG COSIM_USER
ENV COSIM_HOME=/home/$COSIM_USER

# PATH
ENV PATH=$COSIM_HOME/julia-1.9.4/bin:$PATH

# Copy Binaries
#COPY --from=cosim-build:latest $INSTDIR/ $INSTDIR/
#RUN chown -hR $COSIM_USER:$COSIM_USER $COSIM_HOME

# Set as user
USER $COSIM_USER
WORKDIR $COSIM_HOME

RUN echo "Directory structure for running" && \
  wget https://julialang-s3.julialang.org/bin/linux/x64/1.9/julia-1.9.4-linux-x86_64.tar.gz && \
  tar zxvf julia-1.9.4-linux-x86_64.tar.gz  >> "julia.log" && \
  rm julia-1.9.4-linux-x86_64.tar.gz
