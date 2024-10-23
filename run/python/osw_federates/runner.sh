#!/bin/bash

(exec helics_broker -f 1 --loglevel=warning --name=broker &> broker.log &)
(exec python osw_tso.py OSW_TSO osw_lmp_test_scenario &> OSW_TSO.log &)
# (exec python3 simple_federate2.py EVehicle test_scenario &> EVehicle.log &)
# (exec python3 -c "import cosim_toolbox.federateLogger as datalog; datalog.main('FederateLogger', 'test_schema', 'test_scenario')" &> FederateLogger.log &)
