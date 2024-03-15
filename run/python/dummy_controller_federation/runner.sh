#!/bin/bash

(exec helics_broker -f 3 --loglevel=warning --name=broker &> broker.log &)
(exec python3 dummy_controller_fed.py Controller test_DummyController &> Controller.log &)
(exec python3 dummy_market_fed.py Market test_DummyController &> Market.log &)
(exec python3 -c "import cosim_toolbox.federateLogger as datalog; datalog.main('FederateLogger', 'test_DummyControllerSchema', 'test_DummyController')" &> FederateLogger.log &)
