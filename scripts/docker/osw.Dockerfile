# Build runtime image
FROM cosim-python:latest AS cosim-osw

USER root

ARG CST_GRP
ARG CST_USER

ENV CST_HOME=/home/$CST_USER

COPY --from=osw_test_scenario $CST_HOME/egret $CST_HOME/egret
COPY --from=osw_test_scenario $CST_HOME/gridtune $CST_HOME/gridtune
COPY --from=osw_test_scenario $CST_HOME/pyenergymarket $CST_HOME/pyenergymarket
COPY --from=osw_test_scenario $CST_HOME/WECC240_20240807.h5 $CST_HOME/WECC240_20240807.h5

RUN chown -hR $CST_USER:$CST_GRP $CST_HOME

# Set as user
USER $CST_USER
WORKDIR $CST_HOME

RUN echo "pip install for OSW for running" && \
    pip install transitions && \
    pip install --no-warn-script-location --no-cache-dir -e $CST_HOME/egret && \
    pip install --no-warn-script-location --no-cache-dir -e $CST_HOME/pyenergymarket && \
    pip install --no-warn-script-location --no-cache-dir -e $CST_HOME/gridtune
