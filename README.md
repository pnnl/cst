## Overview
This is the internal PNNL repository for the development of Copper (to be renamed before public release). 

Copper is a layer in the E-COMP software stack about HELICS that is intended to provide easy ways to install simulation tools needed by E-COMP, configure the tools for use in a particular use case analysis, run the analysis and post-process the data. Though Copper is use-case agnostic and is being developed by E-COMP, it is expected to be useful by all users of HELICS and will be distributed as a stand-alone product apart from any particular E-COMP-related use cases and analysis.

## Set up development environment

### Prerequisite
You will need to install the following tools:
* python 3.10.x
* make
* docker

For Windows users, it is recommended to use Windows Subsystem for Linux (WSL).

Prerequisite installation for MacOS, Windows, and Linux is out of scope of this instruction. If you have specific question, please contact the team. 

### Create venv
This is to create Python virtual environment dedicated to the local development. The environment will have required dependencies installed automatically.

Before creating venv, if you are working with VPN or inside PNNL network, you need to set proxy for pip to work via the following command:
```
export HTTPS_PROXY=http://proxy01.pnl.gov:3128
export https_proxy=http://proxy01.pnl.gov:3128
```

Create venv with requirements installed:
```commandline
make venv
source venv/bin/activate    # Activate the virtual environment
```
`source venv/bin/activate` activates this virtual environment, so that Python commands you run in your shell use this environment's Python interpreter and installed packages, rather than your system-wide Python installation.

### Run unit tests
```commandline
make test
```
The unit test run will also generate the code coverage report in both XML and HTML. XML report will be used by the pipeline.


### Clean up
The clean-up will delete venv, *.pyc, and coverage files and folders.
```commandline
make clean
```
