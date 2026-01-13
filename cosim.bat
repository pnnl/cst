SCRIPT_PATH="C:\path\to\copper\installation\"
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
set PROJ_DIR=$CST_ROOT/run

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

@REM Populate environment variables to docker files
@REM envsubst < %DOCKER_DIR/env/python.Dockerfile > %DOCKER_DIR/python.Dockerfile
@REM envsubst < %STACK_DIR/env/init-mongo.js > %STACK_DIR/init-mongo.js
@REM envsubst < %STACK_DIR/env/init-db.sql > %STACK_DIR/init-db.sql
