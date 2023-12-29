#!/bin/bash

(exec helics_broker -f 3 --loglevel=warning --name=broker &> broker.log &)
(exec python3 simple_federate.py Battery MyTest &> Battery.log &)
(exec python3 simple_federate.py EVehicle MyTest &> EVehicle.log &)
cd ../../src || exit
(exec python3 data_logger.py DataLogger MySchema MyTest &> ../examples/python_federation/DataLogger.log &)
