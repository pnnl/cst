#!/bin/bash

(exec helics_broker -f 2 --loglevel=warning --name=broker &> broker.log &)
(exec python3 simple_federate.py Battery MyScenario &> Battery.log &)
(exec python3 simple_federate.py EVehicle MyScenario &> EVehicle.log &)
