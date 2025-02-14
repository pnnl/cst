#!/bin/bash

source kill_prev.sh

(exec helics_broker -f 1 --loglevel=warning --name=broker &> broker.log &)
(exec python osw_tso.py OSW_TSO osw_lmp_test_scenario /Users/lill771/Documents/Data/GridView/WECC240_20240807.h5 2032-1-01T00:00:00 2032-01-03T00:00:00 &> OSW_TSO50.log &)
# (exec python osw_plant.py OSW_Plant osw_lmp_test_scenario &> OSW_PLANT51.log &)
# (exec python3 simple_federate2.py EVehicle test_scenario &> EVehicle.log &)
# (exec python -c "import cosim_toolbox.federateLogger as datalog; datalog.main('FederateLogger', 'osw_test_schema', 'osw_lmp_test_scenario')" &> FederateLogger.log &)
