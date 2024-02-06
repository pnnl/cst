#!/bin/bash

(exec helics_broker -f 3 --loglevel=warning --name=broker &> broker.log &)
(exec python3 simple_federate.py Battery test_Scenario &> Battery.log &)
(exec python3 simple_federate2.py EVehicle test_Scenario &> EVehicle.log &)
(exec python3 -c "import cosim_toolbox.federateLogger as datalog; datalog.main('FederateLogger', 'test_Schema', 'test_Scenario')" &> FederateLogger.log &)
