@REM Something like SCRIPT_PATH="C:/Users/kell175/copper"
@REM SCRIPT_PATH="%homedrive%%homepath%/copper"
SCRIPT_PATH="C:\path\to\copper\installation\"
@REM Something like SCRIPT_PATH="MYPYTHON="C:/Users/kell175/AppData/Local/miniconda3/envs/scuc-miniwecc/Lib/site-packages"
MYPYTHON="C:/Users/kell175/AppData/Local/miniconda3/envs/scuc-miniwecc/Lib/site-packages"

@REM Co-simulation user and host
@REM This section should be checked by user before running
set SIM_UID=%UID%
set SIM_USER=%USER%
set SIM_HOST=gage.pnl.gov
set SIM_WSL_HOST=
set SIM_WSL_PORT=
set SIM_DIR=%SCRIPT_PATH%

@REM Co-simulation database, user, password and directory in docker
set COSIM_DB=copper
set COSIM_USER=worker
set COSIM_PASSWORD=worker
set COSIM_HOME=/home/%COSIM_USER%

@REM Co-simulation repo install directories
set BUILD_DIR=%SIM_DIR%/scripts/build
set DOCKER_DIR=%SIM_DIR%/scripts/docker
set STACK_DIR=%SIM_DIR%/scripts/stack

@REM Postgres
@REM set COSIM_POSTGRES_DB=%COSIM_DB
set POSTGRES_HOST=%SIM_HOST%
set POSTGRES_PORT=5432
@REM Launch postgres with admin
set PGADMIN_DEFAULT_EMAIL=user@domain.com
set PGADMIN_DEFAULT_PASSWORD=SuperSecret

@REM Mongo
@REM set COSIM_MONGO_DB=%COSIM_DB
set MONGO_HOST=mongodb://%SIM_HOST%
set MONGO_PORT=27017
@REM Launch mongo with admin
set MONGODB_INITDB_ROOT_USERNAME=admin
set MONGODB_INITDB_ROOT_PASSWORD=SuperSecret

@REM Airflow
@REM add user id for linux
set AIRFLOW_UID=$(id -u)
@REM add user id for windows
@REM set AIRFLOW_UID=50000
set AIRFLOW_GID=0
set AIRFLOW_PROJ_DIR=%SIM_DIR%/run
@REM set _AIRFLOW_WWW_USER_USERNAME=
@REM set _AIRFLOW_WWW_USER_PASSWORD=

@REM Populate environment variables to docker files
@REM envsubst < %DOCKER_DIR%/env/airflow.Dockerfile > %DOCKER_DIR%/airflow.Dockerfile
@REM envsubst < %DOCKER_DIR%/env/jupyter.Dockerfile > %DOCKER_DIR%/jupyter.Dockerfile
@REM envsubst < %DOCKER_DIR%/env/python.Dockerfile > %DOCKER_DIR%/python.Dockerfile
@REM envsubst < %STACK_DIR%/env/init-mongo.js > %STACK_DIR%/init-mongo.js
@REM envsubst < %STACK_DIR%/env/init-db.sql > %STACK_DIR%/init-db.sql

@REM Building without docker define LOCAL_ENV
LOCAL_ENV=no
@REM if [[ -z %LOCAL_ENV ]]; then
@REM   echo "No local environment build variables defined"
@REM else

@REM in dockerfiles REPO_DIR=%COSIM_HOME/repo
@REM set REPO_DIR=%HOME%/grid/repo
@REM set INSTDIR=%HOME%/grid/tenv
@REM set TESPDIR=%REPO_DIR%/tesp
@REM set MESPDIR=%REPO_DIR%/mesp

@REM COMPILE exports
@REM set JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
set PYHELICS_INSTALL="C:/path/to/pyhelics/install"
@REM set GLPATH=%INSTDIR/lib/gridlabd:%INSTDIR%/share/gridlabd
@REM set CPLUS_INCLUDE_PATH=/usr/include/hdf5/serial:%INSTDIR%/include
@REM set FNCS_INCLUDE_DIR=%INSTDIR%/include
@REM set FNCS_LIBRARY=%INSTDIR%/lib
@REM set LD_LIBRARY_PATH=%INSTDIR%/lib
@REM set LD_RUN_PATH=%INSTDIR%/lib
@REM set BENCH_PROFILE=1

@REM PATH exports
set PATH=%INSTDIR%/bin;%PATH%
set PATH=%MYPYTHON%/helics/install/bin;%PATH%
set PATH=%JAVA_HOME%:%PATH%
@REM set PATH=%PATH%;%INSTDIR%/energyplus
@REM set PATH=%PATH%;%INSTDIR%/energyplus/PreProcess
@REM set PATH=%PATH%;%INSTDIR%/energyplus/PostProcess
@REM set PATH=%PATH%;%TESPDIR%/scripts/helpers


@REM PSST environment variables
@REM set PSST_SOLVER=ipopt
@REM set PSST_SOLVER=%INSTDIR/ibm/cplex/bin/x86-64_linux/cplexamp
@REM 'PSST_SOLVER path' -- one of "cbc", "ipopt", "%INSTDIR/ibm/cplex/bin/x86-64_linux/cplexamp"
@REM set PSST_WARNING=ignore
@REM 'PSST_WARNING action' -- one of "error", "ignore", "always", "default", "module", or "once"

@REM PROXY export if needed
@REM set HTTPS_PROXY=http://proxy01.pnl.gov:3128

"C:\path\to\text\editor\or\IDE"