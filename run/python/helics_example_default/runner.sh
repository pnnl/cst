#!/bin/bash

(exec helics_broker -f 3 --loglevel=debug --name=broker &> broker.log &)
(exec python3 battery.py &> Battery.log &)
(exec python3 charger.py &> Charger.log &)
(exec python3 logger.py &> FederateLogger.log &)
