# Running OSW Scenarios

The offshore wind (OSW) market participation scenario is included in this directory.
This guide provides a basic description of the code objectives, installation, and execution.

## OSW Overview

The OSW scenario is intended to assess the effect on the market with OSW plant participation.
The base scenario is the miniWECC (240bus).
There are several research objectives including

1. Determine baseline system behavior with and without the OSW plant
2. Quantify the value added to the system by OSW, particularly in the case of contingencies.
Line outages may be due to wildfire, earthquakes, etc.
3. Quantify other changes to the system such as grid reliability, greenhouse gas reduction, etc.

The market includes a standard two-settlement market with day-ahead (DA) and real-time (RT).
Both markets include reserve products which are co-optimized during market clearing.

The code is built around Co-Sim Toolbox (CST), which includes the HELICS co-simulation platform.
This enables multiple entities to execute their own code as part of the larger simulation. The
collection of entities in HELICS language is a **federation**. Each entity operates as a **federate**.

The OSW scenario has two federates within its federation.
1. `osw_tso.py`: This models the offshore wind (OSW) transmission system operator (TSO).
The OSW_TSO job is to collect bids, join them with system information from the miniWECC, and
clear the market(s). OSW_TSO handles the market timing and determines the dispatch and settlements
for all generators.
2. `osw_plant.py`: The offshore wind plant. The job of this script is to retrieve data from the OSW_TSO,
such as load, renewable, and price forecasts, and develop a bid. This bid is returned to the OSW_TSO to
incorporate in market clearings.

The federation operates these two federates in tandem, proceeding through a user-specified data range. Results
are published to a SQL postgres database for retrieval and analysis.

## Installation

Get yourself a cup of coffee or
tea before getting started; this will take a little while.

### Cloning Repositories

The OSW scenario requires several GitHub/GitLab repositories to run. All repos are
private/access controlled; **please contact your project lead to gain access**. These are:
1. Copper/Co-Sim Toolbox: `integrate_egret` branch (https://devops.pnnl.gov/e-comp/thrust-3/copper)
2. PyEnergyMarket: `main` branch (https://devops.pnnl.gov/e-comp/thrust-3/pyenergymarket)
3. Egret: `develop` branch (https://github.com/pnnl-private/egret/)
4. GridTUNE `main` branch (https://tanuki.pnnl.gov/gridtune/gridtune)
Note that branch information is subject to change during development.

### Setting up your Python Environment

Once you have downloaded all of the repos, the instructions below will allow you to
set up your local environment. This will enable you to run test scenarios on your local machine.
Disclaimer: Code is under development so some of the following details may change. Please contact
your project lead if you unable to complete the installation.

1. You have two options for the first step. depending on your preferred environment method (venv or conde)

Option A `venv`: 

*Inside the Copper repo* follow the instructions on the copper README. This should end
with executing the command `source venv/bin/activate`. **Ensure the the virtual environment
is active before proceeding**.

Option B `conda`:

Create a conda environment: `conda create --name osw`. Activate the conda environment: `conda activate osw`. Navigate to `copper/src/cosim_toolbox` and run `pip install -e .`

2. *Inside the PyEnergyMarket repo* follow the instructions on the PyEnergyMarket README.
Note that this includes instructions for installing requirements for both Egret and GridTUNE.
3. `pip install transitions`
4. Navigate to `copper/src/cosim_toolbox` and run `pip install -e .` ***TODO We shouldn't have to run this again.
Check if a path is getting overwritten when installing PyEnergyMarket***

You may optionally run the tests described in the Copper and PyEnergyMarket README files to
verify successful installation.

## Execution (Locally)

### Setting up the PNNL environmental variables

Before starting you must **activate the cosim environment**. This must be done every time you
restart your Python environment. The `cosim.env` script will set all of the
necessary paths to the PNNL Mongo database and Postgres database as well as default user credentials.
Navigate to the top level of
the copper repo and run

`source cosim.env`

**MacOSX users only**: This command will fail. You must first edit cosim.env. Change the line:

`export CST_HOST=$(hostname -A | awk '{print $1}')`

to

`export CST_HOST=gage.pnl.gov`

You may also need to deactivate the local environment. This is done by changing line

`LOCAL_ENV=yes`

to

`LOCAL_ENV=""`

### Accessing the miniWECC scenario

The miniWECC system is saved in an H5 file on the ECOMP shared drive. Please
contact your project lead for access. The path is:

Windows: `\\PNL\Projects\ECOMP\Shared Data\H5Files\WECC240_20240807.h5`
MacOSX: `smb://pnl/Projects/ECOMP/Shared Data/H5Files/WECC240_20240807.h5`

Note MacOSX users will need to mount the `Shared Data` folder (through Finder -> Go -> Connect to Server
-> enter `smb://pnl/Projects/ECOMP/Shared Data`) to use PyEnergyMarket tests.

Optionally, you may download a local copy of this H5 file to your system. Please place it **outside
of the repos**. Whether local or on the shared drive, note the path you used (hereafter: `<path-to-WECC-h5>`).

### Setting up your test scenario

The first time you execute `runner.py` the code will create the file `runner_config.json` and exit.
You may edit `runner_config.json` to set up your specific scenario. There are multiple options you can
change here; for now we focus on the minimum changes to begin execution.

1. Change `h5path` to your local/network H5 file path `<path-to-WECC-h5>`.
2. Set your desired beginning time and ending time/date (running 2 days is a good starting test). These are
string formatted as YYYY-mm-ddTHH:MM:SS (such as "2032-01-01T00:00:00") 
3. Set up your custom schema and scenario. This controls the save location within the Postgres database. Your exact name choices can vary.
If you chose a name with an existing schema or scenario, you will be asked whether to overwrite this or not. Ensure you only overwrite
scenarios if you are the creator or have permission from the creator.
4. If using the offshore wind plant, set `include_plant` to `true`, otherwise use `false`.

You may now run

`python runner.py`

If this fails, ensure you have run `source cosim.env` and are connected to the PNNL VPN.

### Executing your scenario

Running the `runner.py` will automatically create a shell file titled `{scenario_name}.sh`. You can start a scenario with `./{scenario_name}.sh`. 
You may view the rolling output with the command `tail -f {log_name}.log}` or `less +F {log_name}.log}`. The default for `log_name` is `OSW_TSO`.

When `osw_tso.py` is executed (this is done by `{scenario_name}.sh`), it will create the file `options_osw.json`. This file
has various simulation settings that you may edit to customize your run, although the defaults are generally a good starting point.

Note that if a scenario encounters an error, the helics broker will
not be stopped. You may need to run `./kill_prev.sh` or manually kill any hung processes before re-starting the scenario.
This may require changing permissions using `chmod u+x kill_prev.sh`.

### Retrieving your results

The data from your scenario is published to the Postgres database, hosted on gage.pnl.gov,
with your schema and scenario names. To retrieve this, run

`python retrieve_records.py`

This will notify you that it has created the file `query_info.json`. Edit this file to include
your `schema_name` and your `scenario_name`. You may also change other variables as you see fit.

Now repeat the command `python retrieve_records.py` and your data will be downloaded to the `data` folder
(which is created if it didn't already exist). You can view the CSV files
`da_price_results.csv`, `da_reserve_results.csv`, `rt_price_results.csv`, and `rt_dispatch_results.csv`.
There is also an h5 file created which contains all results.

## Execution (Docker)

### Prerequisites

It will be necessary to have a Docker account to proceed with execution. Ensure that you can log in to Docker before proceeding. 
Accessing the Docker container must be done through gage. Please contact your project lead if you are unable to access gage. To access gage from your command line, run `ssh {username}@gage.pnl.gov` in your command line and input your password.  

Once in gage, clone the Copper/Co-Sim Toolbox repository: `integrate_egret` branch. 

**Note that the `copper/run` directory is mounted to the Docker container, so any change made to anything under this directory on gage will change inside of the Docker container as well!**

**Also note that files cannot be modified within the Docker container. You must exit the container, modify the appropriate file within the `copper/run` directory on gage, and then re-enter the Docker container.**

### Accessing the Docker constainer

Ensure that you are logged into gage before proceeding. Navigate inside of the Copper repo execute the command `source venv/bin/activate`. Ensure the environment is active before proceeding.
It is also necessary to follow the **Setting up the PNNL environmental variables** instructions under **Execution (Locally)**.

To access the Docker image, navigate to the `copper/scripts` directory and run `./runcosim.sh`.
This will take you inside of the Docker container. 

### Setting up your test scenario

The steps here are identical to those in this section under **Execution (Locally)** with a few notable changes. First, the H5 file we are using for runs is inside of the `home/worker` directory of the Docker image. The Docker does not have access to the ECOMP shared drive, so please ensure use the path to the H5 file already inside of the container. 

Lastly, to run the `runner.py`, it is necessary to use `python3 runner.py`. If you receive a Permission denied error after running that prevents creation of the shell script, you will need to navigate to the `copper/run` directory and change your permissions by executing `chmod -R 775 *`. 

### Executing your scenario

Running the `runner.py` will automatically create a shell file titled `{scenario_name}.sh`. You can start a scenario with `./{scenario_name}.sh`. 
You may view the rolling output with the command `tail -f {log_name}.log}`. Results can then be retrieved by following the **Retrieving your results** section of **Execution (Locally)**.