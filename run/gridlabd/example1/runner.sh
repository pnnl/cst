#!/bin/bash

(exec helics_broker -f 3 --loglevel=debug --name=broker &> broker.log &)
(exec python3 controller.py &> Controller.log &)
(exec python3 federateGridlabD.py &> FederateGridlabD.log &)
(exec python3 logger.py &> FederateLogger.log &)
