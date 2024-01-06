#!/bin/bash

(exec helics_broker -f 3 --loglevel=warning --name=broker &> broker.log &)
(exec python3 simple_federate.py Battery test_MyTest &> Battery.log &)
(exec python3 simple_federate2.py EVehicle test_MyTest &> EVehicle.log &)
cd ../../src || exit
(exec python3 data_logger.py DataLogger test_MySchema2 test_MyTest &> ../examples/test_federation/DataLogger.log &)
