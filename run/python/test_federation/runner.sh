#!/bin/bash

(exec helics_broker -f 2 --loglevel=warning --name=broker &> broker.log &)
(exec python3 simple_federate.py Battery test_scenario &> Battery.log &)
(exec python3 simple_federate2.py EVehicle test_scenario &> EVehicle.log &)
#(exec python3 -c "import cosim_toolbox.federateLogger as datalog; datalog.main('FederateLogger', 'test_schema', 'test_scenario')" &> FederateLogger.log &)
