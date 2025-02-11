#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  echo "Edit cosim.env in the CoSimulation Toolbox directory"
  echo "Run 'source cosim.env' in that same directory"
  exit
fi

JAVAPATH=${INSTDIR}/java

cd "${BUILD_DIR}" || exit
if ! [ -f "test_helics.class" ]; then
  javac -classpath ".:$JAVAPATH/helics.jar" test_helics.java
  java -classpath ".:$JAVAPATH/helics.jar" -Djava.library.path="$JAVAPATH" test_helics
fi
