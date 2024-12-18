#!/bin/bash

lt=$(TZ='America/Los_Angeles' date)

# remove semaphore
rm -rf finished.txt

# capture server name
cat /etc/hostname > hostname

# manually run every so often a check to see if we can quit this script
while sleep 60; do
  ps aux | grep federate | grep -q -v grep
  PROCESS_1_STATUS=$?
  ps aux | grep helics_broker | grep -q -v grep
  PROCESS_3_STATUS=$?
  # If the greps above find anything, they exit with 0 status
  # If all are not 0, then we are done with the main background processes
  if [ $PROCESS_1_STATUS -ne 0 ] && [ $PROCESS_3_STATUS -ne 0 ]; then
    # All processes are federate, helics_broker
    # TODO: then, massage stats.log into slightly easier-to-read TSV with: sed -i 's/./&"/68;s/$/"/;$d' stats.log
    #  which wraps the commands in quotes and removes the last line which could be cut off
    # add semaphore
    echo "Start: $lt "$'\n'"Done: $(TZ='America/Los_Angeles' date)" > finished.txt
    exit 1
  fi
done
