# cosim_toolbox Python files

Copyright (c) 2022-2025 Battelle Memorial Institute

This is the main code repository for Python-based components of CoSimulation Toolbox. 

TODO

### File Directory

- *__init__.py*; boilerplate for a Python package
- *bench_profile.py*; small profiler to gather resource stats  
- *dbConfigs.py*; Provides methods to read and write to the metadata database.
- *dbResults.py*; Methods for writing to and reading from the time-series database.
- *dockerRunner.py*; Collection of static methods used in building and running the docker-compose.yaml for running a new service or simulator.
- *federate.py*; Federate class that defines the basic operations of Python-based federates
- *federateLogger.py*; Data logger class that defines the basic operations of Python-based logger federate
- *federation.py*; Defines the Federation class which is used to programmatically define a federation of federate class modules
- *helicsConfig.py*; Defines the HelicsMsg class which is used to programmatically define pubs and subs of a HELICS class
- *readConfig.py* Class to open a Mongo Database to retrieve scenario data (metadata)
- *README.md*; this file

### Subdirectories

None
