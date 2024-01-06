#!/bin/bash

(exec helics_broker -f 3 --loglevel=warning --name=broker &> broker.log &)
(exec python3 simple_federate.py Battery MyScenario &> Battery.log &)
(exec python3 simple_federate.py EVehicle MyScenario &> EVehicle.log &)
(exec python3 -c "import cosim_toolbox.data_logger as datalog; datalog.main('DataLogger', 'MySchema', 'MyScenario')" &> DataLogger.log &)
