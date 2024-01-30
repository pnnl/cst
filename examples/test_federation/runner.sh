#!/bin/bash

(exec helics_broker -f 3 --loglevel=warning --name=broker &> broker.log &)
(exec python3 simple_federate.py Battery test_MyTest &> Battery.log &)
(exec python3 simple_federate2.py EVehicle test_MyTest &> EVehicle.log &)
(exec python3 -c "import cosim_toolbox.data_logger as datalog; datalog.main('DataLogger', 'test_MySchema2', 'test_MyTest')" &> DataLogger.log &)