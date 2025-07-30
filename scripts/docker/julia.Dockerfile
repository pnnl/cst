# Build runtime image
FROM cosim-cst:latest AS cosim-julia

USER root

ARG CST_USER
ENV CST_HOME=/home/$CST_USER

# PATH
ENV PATH=$CST_HOME/julia-1.9.4/bin:$PATH

# Copy Binaries
#COPY --from=cosim-build:latest $INSTDIR/ $INSTDIR/
#RUN chown -hR $CST_USER:$CST_GRP $CST_HOME

# Set as user
USER $CST_USER
WORKDIR $CST_HOME

RUN echo "Directory structure for running" && \
  wget https://julialang-s3.julialang.org/bin/linux/x64/1.9/julia-1.9.4-linux-x86_64.tar.gz && \
  tar zxvf julia-1.9.4-linux-x86_64.tar.gz  >> "julia.log" && \
  rm julia-1.9.4-linux-x86_64.tar.gz
