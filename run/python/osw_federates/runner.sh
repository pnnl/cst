#!/bin/bash

(exec helics_broker -f 3 --loglevel=warning --name=broker &> broker.log &)
(exec python osw_tso.py OSW_TSO osw_lmp_test_scenario &> OSW_TSO.log &)
(exec python osw_plant.py OSW_Plant osw_lmp_test_scenario &> OSW_PLANT.log &)
# (exec python3 simple_federate2.py EVehicle test_scenario &> EVehicle.log &)
(exec python -c "import cosim_toolbox.federateLogger as datalog; datalog.main('FederateLogger', 'osw_test_schema', 'osw_lmp_test_scenario')" &> FederateLogger.log &)
