#!/bin/bash

pid_array=()
while IFS= read -r line; do
  pid_array+=( "$line" )
done < <( ps -ef | grep -v grep | grep osw_federates | awk '{print $2}' )

for i in "${pid_array[@]}"
do
  echo "Killing process $i"
  kill -9 "$i"
done
