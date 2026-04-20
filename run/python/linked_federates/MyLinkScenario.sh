#!/bin/bash

(exec helics_broker -f 2 --loglevel=warning --name=broker &> broker.log &)
(exec python3 simple_federate.py Battery MyLinkScenario json csv &> Battery.log &)
(exec python3 simple_federate2.py EVehicle MyLinkScenario json csv &> EVehicle.log &)
