#!/bin/bash

(exec helics_broker -f 2 --loglevel=warning --name=broker &> broker.log &)
(exec python3 simple_federate.py Battery MyTest &> Battery.log &)
(exec python3 simple_federate.py EVehicle MyTest &> EVehicle.log &)
