# Configuring Analysis in CoSim Toolbox

**TODO:** TDH - I think the contents of each of these configuration files needs to be reviewed and rationalized to help users understand which information should go where. As I don't have a working knowledge of how these are used I don't want to be prescriptive but it is clear to me in just reviewing these that a revision on there structure is likely necessary.

Much of the challenge of setting up and running co-simulations is expressed in getting all the components of the cosimulation cofigured correctly. This is not only limited to the configuration of the information exchange in the co-simulation proper but also the configuration of the non-co-simulation aspects of the federates operation (_e.g._ which model file to load, what input datasets to use) but also the definition of parameters that impact multiple federates. To address these challenges, CoSim Toolbox defines the configuration of the analysis in a number of specific parts:

- Federate configuration - Configures the launch of the federate in CoSim Toolbox
- Federation configuration - Configures the connection between federates to form a co-simulation federation
- Scenario configuration - Configures co-simulation values that are generally useful to all entities in the analysis, including those that might run as pre- or post-processing steps

As of this writing (Sept 2024), there is no tooling in place to assist in the creation of these files. This document will provide guidance on the information that needs to be defined in these files for CoSim Toolbox to function properly. Additional information that is useful to a co-simulation modeler can also be stored in these files without compromising their functionality in CoSim Toolbox. The information in these files is expected to be loaded into the CoSim Toolbox metadata database using provided APIs as a part of preparing to run a co-simulation. Some of this configuration data transcends a given analysis and thus may already exist in the metadata database prior to beginning configuration of the co-simulation. Other information will likely need to be loaded into the metadata database prior to any run. in either case, knowing the contents of the configuration already in the database can reduce the configuration workload for a given analysis.

As is the case for most of the metadata database content, the data stored is structured text and can be thought of as a JSON or Python dictionary. CoSim Toolbox APIs are provided for loading and reading these in-memory elements to and from the metadata database.

## Federate Configuration

The federate configuration defines how a given federate will be launched as a federate managed by CoSim Toolbox. At the highest level of the structure is an object that defines a name and docker image that is available for federates to use as their execution environment. For example, the federate configuration may begin define a Python environment like this:

```json
{
    "cu_name": "helics",
    "image": "cosim-helics:latest"
}
```
 
In addition to this, each federate object may include environment variables that should be set when any federate runs:

```json
  {
    "environment": {
      POSTGRES_HOST: "${POSTGRES_HOST}",
      POSTGRES_PORT: "${POSTGRES_PORT}",
      COSIM_DB: "${COSIM_DB}",
      COSIM_USER: "${COSIM_USER}",
      COSIM_PASSWORD: "${COSIM_PASSWORD}"
    }
  }
```

Each federate the uses this execution environment also defines a launch command and a few co-simulation specific values such as the type of HELICS federate ("value", "message", or "combination") and the simulation step size.

```json
"commands": [
      { "command": "/bin/bash -c \"exec helics_broker --ipv4 -f 3 --loglevel=warning --name=broker\"",
        "federate_type": "value",
        "time_step": 120 },
      { "command": "/bin/bash -c \"exec helics_player\"",
        "federate_type": "value",
        "time_step": 120 }
    ]
```

An example of a federate configuration JSON is shown below, including the reserved name "cu_name" for use by CoSim Toolbox to know where to look for this configuration information.

```json
[
  {
    "cu_name": "federate documents"
  },
  {
    "cu_name": "python",
    "image": "cosim-python:latest",
    "environment": {
      POSTGRES_HOST: "${POSTGRES_HOST}",
      POSTGRES_PORT: "${POSTGRES_PORT}",
      COSIM_DB: "${COSIM_DB}",
      COSIM_USER: "${COSIM_USER}",
      COSIM_PASSWORD: "${COSIM_PASSWORD}"
    },
    "commands": [
      {
        "federate": "logger",
        "command": "/bin/bash -c \"source /home/worker/venv/bin/activate && exec python3 -c \"import cosim_toolbox.federateLogger as datalog; datalog.main('FederateLogger', 'test_Schema', 'test_Scenario')\"",
        "federate_type": "value",
        "time_step": 120
      },
      {
        "federate": "battery",
        "command": "/bin/bash -c \"source /home/worker/venv/bin/activate && exec python3 simple_federate2.py Battery test_Scenario\"",
        "federate_type": "value",
        "time_step": 120
      },
      {
        "federate": "eVehicle",
        "command": "/bin/bash -c \"source /home/worker/venv/bin/activate && exec python3 simple_federate2.py Battery test_Scenario\"",
        "federate_type": "value",
        "time_step": 120
      }
    ]
  }
]
```

## Federation Configuration

**TODO:** TDH - There is redundant information in the federate and federation configfuration sample JSONs, specifically, "image" and "time_step" show up in both. I don't know why "time_step" even exists as a separate entry as it seems like the HELICS configuration information should be the place to hold the timing data.

**TODO:** TDH - I would have thought that the federation JSON would somehow reference the federate information to allow the federate information to be reusable. Again, not having used this, I might be missing something important.

The primary goal of the federation configuration information is to define the HELICS co-simulation connection information; this is likely to take up the majority of the content in the configuration object. There are a few additional parameters (some redundant with the federate configuration information; don't ask me why) that are defined. A complete example of the federation configuration is shown below.

**TODO:** TDH - Is "cu_name" supposed to be in both objects below?

```json
[
  {
    "cu_name": "federation documents"
  },
  {
    "cu_name": "BT1_EV1",
    "federation": {
      "Battery": {
        "image": "python/3.11.7-slim-bullseye",
        "command": "exec python3 simple_federate.py TE30 EVehicle",
        "federate_type": "value",
        "time_step": 120,
        "HELICS_config": {
          "name": "Battery",
          "core_type": "zmq",
          "log_level": "warning",
          "period": 60,
          "uninterruptible": false,
          "terminate_on_error": true,
          "wait_for_current_time_update": true,
          "publications": [
            {
              "global": true,
              "key": "Battery/EV1_current",
              "type": "double",
              "unit": "A"
            }
          ],
          "subscriptions": [
            {
              "global": true,
              "key": "EVehicle/EV1_voltage",
              "type": "double",
              "unit": "V"
            }
          ]
        }
      },
      "EVehicle": {
        "image": "python/3.11.7-slim-bullseye",
        "command": "exec python3 simple_federate.py TE30 EVehicle",
        "federate_type": "value",
        "time_step": 120,
        "HELICS config": {
          "name": "EVehicle",
          "core_type": "zmq",
          "log_level": "warning",
          "period": 60,
          "uninterruptible": false,
          "terminate_on_error": true,
          "wait_for_current_time_update": true,
          "publications": [
            {
              "global": true,
              "key": "EVehicle/EV1_current",
              "type": "double",
              "unit": "V"
            }
          ],
          "subscriptions": [
            {
              "global": true,
              "key": "Battery/EV1_voltage",
              "type": "double",
              "unit": "A"
            }
          ]
        }
      }
    }
  }
]
```

As is the case in the federate configuration definition, there is a reservered item "cu_name" that is used by CoSim Toolbox to find this information in the database. A name for the federation must be define (TODO: as "cu_name"?) and then the federation object holds definitions for each federate in the federation. This includes the Docker image in which the federate will run, the command to launch the federate, and literal HELICS configuration that is used to configure the federate to be a part of the federation

## Scenario Configuration

In CoSim Toolbox, any time a co-simulation is run, it is considered to be an execution of a "scenario". An analysis as a whole will often contain multiple scenarios, typically comparing the behvarior of a system under similar but distinct conditions. For example, using the context of an EV charging analysis, there could be multiple scenarios where the maximum charging power of the EVs is varied. Generally, the data collected and the metrics calculated across scenarios is very similar to enable the direct comparison of the impacts of changing specific model parameters (_e.g._ EV charging power).

Thus, it is typical that a unique scenario configuration is created each time a given federation is run. Storing this scneario configuration information in the metadata database provides an artifiact that can be examined to understand the differences between scenarios and is useful when performing post-processing as it makes cross-scenario comparison more easily understood.

An example of a scenario configuration is provided below:

```json
[
  {
    "cu_name": "scenario documents"
  },
  {
    "cu_name": "TE30",
    "start_time": "2023-12-07T15:31:27",
    "stop_stime": "2023-12-07T15:31:27",
    "federation": "BT1_EV1",
    "schema": "Tesp",
    "docker": true
  }
]
```

As before, the "cu_name" is a reserved key that allows CoSim Toolbox to find this configuration information. In this configuration, each object must be given a unique name and reference the "federation" configuration it will be using. The simulation start and stop time must be defined (**TODO:** Is this true or are these customer parameters?)

**TODO:** What is the "docker" parameter for?

