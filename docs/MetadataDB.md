# Metadata (Configuration) Management
It is not unusual for a study to include a sufficient number of scenarios (see the [Terminology page](./Terminology) for how CST uses these terms) that are defined over a sufficiently lengthy period of time that at the conclusion of the experiementation (_i.e._ simulation runs) there is less than absolutely clarity about which parameters applied to which scenarios. Even when the set of scenarios is well-defined in advance, it is not unusual for pre-liminary results to inspire new scenarios with new parameters not included in the original set. All of this is complicated in a co-simulation by the number of federates and the management of their configuration files. 

To help manage this, CoSim Toolbox (CST) provides a metadata data store as a means for storing metadata related to the analysis.  CST provides two data stores: a MongoDB server and a local directory for CSVs; the MongoDB server and an inspector ("Mongo Express") are included as part of CST's "persistent services". CST provides identical APIs ("backends") for accessing both. CST itself uses these APIs to store and retrieve the configuration data for each federate, much of which is HELICS-specific. The APIs are also available for modelers to use to store their own custom data, allowing scenarios to be defined in ways that are helpful.

## Data Schema
OK, as you might guess, the key advanatage of storing JSON-like objects as records (Python dictionaries, "documents" in MongoDB parlance) is that they are not required to have a tabular structure. That is, each record is not required to have the same elements (columns). That said, there are two dictionaries that CST uses that do have a specific structure: the "federations" and "scenarios" dictionaries. It is the responsibilty of the analysis team to create these and upload them to the metadata data store prior to trying to run the co-simulation. These dictionaries are held in groups (called "collections" by MongoDB) of the same names.

### "scenarios"
Each dictionary in the "scenarios" defines a few key specific parameters that are needed to run the co-simulation:
- "analysis" (str) - Name of the analysis to which this scenario belongs (see the [Terminology page](./Terminology) for further details)
- "federations" (str) - Name of the federation dictionary use for this analysis
- "start_time" (str) - Start of the simulation time in ISO 8601 format
- "start_time" (str) -Stop of the simulation time in ISO 8601 format
- "docker" (bool) - Indicates whether Docker containers are used to run any of the federates
- "cst_007" (str) - **Not directly defined by user.** Name assigned to the scenario dictionary by the user when added to the metadata data store and added to the dictionary by CST

In addition to these required parameters, modelers can add any number of custom parameters to the dictionary; these will not affect the operation of CST and will be stored in the metadata data store for later use by a modeler. An example scenario dicionary, including a few custom values, would look like the following:

```json
{
    "analysis": "MyAnalysis",
    "federation": "MyFederation",
    "start_time": "2023-12-07T15:31:27",
    "stop_time": "2023-12-08T15:31:27",
    "docker": false,
    "cst_007": "MyScenario",
    "EV penetration": 0.2,
    "location": "California"
}

```

This document must be added to the metadata data store prior to running a co-simulation as CST uses it to correctly instantiate the federates and run the co-simulation.


### "federations" 
The "federation" dictionary holds the definition of the federation being constructed to run the co-simulation. Virtually all of this information is a definition of each federate in the federation, including the commands to run to launch the federate as well as the HELICS configuration information. We're not going to go over all the possible HELICS configuration values here (HELICS documents that on their ["Configuration Options Reference" page](https://docs.helics.org/en/latest/references/configuration_options_reference.html) and provides [lots of examples](https://docs.helics.org/en/latest/user-guide/examples/examples_index.html)) but getting this configuration defined correctly is an essential part of having the co-simulation run correctly. The dictionary is structured as follows:

```json
{
    "cst_007":,  
    "federation": {
        "federate1":{
           "logger":, 
            "image":, 
            "command":, 
            "HELICS_config":{
            }
        },

    }
}
```

- "cst_007" (str) - **Not directly defined by user.** Name assigned to the scenario dictionary by the user when added to the metadata data store and added to the dictionary by CST
- "federation (str) - Holds all the configuration information for the federation
- "logger" (str) - Indicates whether any publications created by this federate should be automatically collected and put into the time-series data store
- "image" (str) - The name of the Docker image containing the simulator for this federate. If a Docker image is not being used, this can be left as a null string ("").
- "command" (str) - The command line run to execute the simulation for this federate. If using a Docker image, this is the command that will run when the image is stood up. If using a simulator installed on the host system, this is the command run on the system shell.

Below is an example of a more completely defined "federation" dictionary.

```json
{
    "cst_007": "ExampleFederation",
    "federation": {
        "Battery": {
            "logger": false,
            "image": "cosim-cst:latest",
            "command": "python3 simple_federate.py Battery test_scenario",
            "HELICS_config": {
                "name": "Battery",
                "log_level": "warning",
                "period": 30,
                "broker_address": "10.5.0.2",
                "terminate_on_error": true,
                "tags": {
                    "logger": "yes"
                },
                "publications": {
                    "key": "Battery/current",
                    "type": "double",
                    "unit": "A",
                    "global": true,
                    "tags": {
                        "logger": "yes"
                    }
                },
                "subscriptions": {
                    "key": "EVehicle/voltage",
                    "type": "double",
                    "unit": "V"
                },
                "endpoints": {

                }

            }

        },
        "federate2": {

        }
    }
}
```


## Using CST's metadata data store
There is comprehensive documentation on the metadata backend APIs provided by CST in the [API documentation section](./References.rst) and we're not going to replicate it all here. Virtually all of the "federation" and "scenario" dictionaries need only to be defined and written in once. For example, if you're conducting a study evaluating the impact on distribution system voltage as EV penetration increases, you may define five scenarios where the EV penetration is 0%, 20%, 40%, 60%, and 80%. Once you've defined the parameters for these scenarios and written them to the metadata data store, they don't need to be re-written every time you run one of the scenarios (unless a parameter value changes). 

The following is an example of how to use the CST APIs to write a scenario dictionary into the CSV metadata data store.

```python


```
