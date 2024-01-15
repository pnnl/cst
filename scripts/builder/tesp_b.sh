#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  . "${HOME}/tespEnv"
fi

# Compile TESP energyplus agents
cd "${REPODIR}/tesp/src/energyplus" || exit
# the following steps are also in go.sh
autoheader
aclocal
automake --add-missing
autoconf
./configure --prefix="${INSTDIR}" --with-fncs="${INSTDIR}" 'CXXFLAGS=-w -O2' 'CFLAGS=-w -O2'
if [[ $1 == "clean" ]]; then
  make clean
fi
make -j "$(grep -c "^processor" /proc/cpuinfo)"
make install

# Compile TESP TMY3toTMY2_ansi
cd "${REPODIR}/tesp/data/weather/TMY2EPW/source_code" || exit
gcc TMY3toTMY2_ansi.c -o TMY3toTMY2_ansi
mv -f TMY3toTMY2_ansi "${INSTDIR}/bin"
