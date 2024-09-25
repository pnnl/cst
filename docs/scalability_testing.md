# Scalability Testing 

## Motivation

E-COMP leadership has prioritized scalability testing for CST as a "no-regrets" activity that can be started early in FY25. The purposes of this activity are as follows:

1. Demonstrate the scalability of CST to at least 100 federates. Though this may not be in doubt to us close to the software, having it demonstrated bring credibility to the platform and creates a talking point for the software.
2. Identify low-performing code in CoSim Toolbox for improvement

To this end, we will be building and conducting scability testing in Oct FY25 to determine the impact of using CST when performing a HELICS-based co-simulation.

## Experiment Requirements

1. Easily scalable to an arbitrarily large number of federates.
2. Uses federate.py
3. Uses metadata database and time-series database 
4. Produces sufficient data to exercise the time-series database via logger.py
5. Federation execution time instrumentation
6. Needs to be able to be run without CST as baseline
    - Same number of federates and same federation topology
    - No Docker
    - Writing to file rather than database
    - Local configuration JSON files, no configuration via APIs
    - Launching by same mechanism (runner.py)
    - Use the same version of Python locally as in the Docker environment



## Experiment Design

The CST scalability experiment will have the following parameters and values:

1. Number of federates: [10, 100, 1000]
2. Number of pubs and subs per federate [1, 10, 100]
3. Use of endpoints [true, false]
4. Use of CST [true, false]
5. Use of profiling [true, false]

A full factorial version of this study is as follows:

| Scenario | Fed. Count | Pub Count | Endpoints | Use CST | Use Profiling |
| -------- |----------- | --------- | --------- | ------- | ------------- |
| 1        | 10         | 1         | false     | false   | false         |
| 2        | 100        | 1         | false     | false   | false         |
| 3        | 1000       | 1         | false     | false   | false         |
| 4        | 10         | 10        | false     | false   | false         |
| 5        | 100        | 10        | false     | false   | false         |
| 6        | 1000       | 10        | false     | false   | false         |
| 7        | 10         | 100       | false     | false   | false         |
| 8        | 100        | 100       | false     | false   | false         |
| 9        | 1000       | 100       | false     | false   | false         |
| 10       | 10         | 1         | true      | false   | false         |
| 11       | 100        | 1         | true      | false   | false         |
| 12       | 1000       | 1         | true      | false   | false         |
| 13       | 10         | 10        | true      | false   | false         |
| 14       | 100        | 10        | true      | false   | false         |
| 15       | 1000       | 10        | true      | false   | false         |
| 16       | 10         | 100       | true      | false   | false         |
| 17       | 100        | 100       | true      | false   | false         |
| 18       | 1000       | 100       | true      | false   | false         |
| 19       | 10         | 1         | false     | true    | false         |
| 20       | 100        | 1         | false     | true    | false         |
| 21       | 1000       | 1         | false     | true    | false         |
| 22       | 10         | 10        | false     | true    | false         |
| 23       | 100        | 10        | false     | true    | false         |
| 24       | 1000       | 10        | false     | true    | false         |
| 25       | 10         | 100       | false     | true    | false         |
| 26       | 100        | 100       | false     | true    | false         |
| 27       | 1000       | 100       | false     | true    | false         |
| 28       | 10         | 1         | true      | true    | false         |
| 29       | 100        | 1         | true      | true    | false         |
| 30       | 1000       | 1         | true      | true    | false         |
| 31       | 10         | 10        | true      | true    | false         |
| 32       | 100        | 10        | true      | true    | false         |
| 33       | 1000       | 10        | true      | true    | false         |
| 34       | 10         | 100       | true      | true    | false         |
| 35       | 100        | 100       | true      | true    | false         |
| 36       | 1000       | 100       | true      | true    | false         |
| 37       | 10         | 1         | false     | false   | true          |
| 38       | 100        | 1         | false     | false   | true          |
| 39       | 1000       | 1         | false     | false   | true          |
| 40       | 10         | 10        | false     | false   | true          |
| 41       | 100        | 10        | false     | false   | true          |
| 42       | 1000       | 10        | false     | false   | true          |
| 43       | 10         | 100       | false     | false   | true          |
| 44       | 100        | 100       | false     | false   | true          |
| 45       | 1000       | 100       | false     | false   | true          |
| 46       | 10         | 1         | true      | false   | true          |
| 47       | 100        | 1         | true      | false   | true          |
| 48       | 1000       | 1         | true      | false   | true          |
| 49       | 10         | 10        | true      | false   | true          |
| 50       | 100        | 10        | true      | false   | true          |
| 51       | 1000       | 10        | true      | false   | true          |
| 52       | 10         | 100       | true      | false   | true          |
| 53       | 100        | 100       | true      | false   | true          |
| 54       | 1000       | 100       | true      | false   | true          |
| 55       | 10         | 1         | false     | true    | true          |
| 56       | 100        | 1         | false     | true    | true          |
| 57       | 1000       | 1         | false     | true    | true          |
| 58       | 10         | 10        | false     | true    | true          |
| 59       | 100        | 10        | false     | true    | true          |
| 60       | 1000       | 10        | false     | true    | true          |
| 61       | 10         | 100       | false     | true    | true          |
| 62       | 100        | 100       | false     | true    | true          |
| 63       | 1000       | 100       | false     | true    | true          |
| 64       | 10         | 1         | true      | true    | true          |
| 65       | 100        | 1         | true      | true    | true          |
| 66       | 1000       | 1         | true      | true    | true          |
| 67       | 10         | 10        | true      | true    | true          |
| 68       | 100        | 10        | true      | true    | true          |
| 69       | 1000       | 10        | true      | true    | true          |
| 70       | 10         | 100       | true      | true    | true          |
| 71       | 100        | 100       | true      | true    | true          |
| 72       | 1000       | 100       | true      | true    | true          |

The use of profiling is a stretch goal for this effort so the bottom half of the scenarios may not be evaluated. 


### Test Federation Topology
To stress test CST, the test federation will be simple. A ring of federates will be defined where a given federate will subscribe to all the publications (and become a target for its endpoint when applicable) from the federate before it and publish value to (and send messages to) the federate after it. 


### Experiment Creation
The federation will create the following files on disk (_x_ is the number of federates and _m_ is the scenario test designator)

1. **federate_x_config.json** - HELICS configuration JSON for a given federate
2. **cst_federate.json** - Federate defintion information used by CST
3. **cst_federation.json** - Federation definition information used by CST
4. **cst_scenario_m.json** - Scenario definition information used by CST

The files will be arranged as follows (for example when scenario m = 7)
```
cst_scalability_experiment
|---...
|---scenario_7
    |---federate_configs
        |---federate_1_config.json
        |---federate_2_config.json
        |---federate_3_config.json
        ...
    |---cst_federate.json
    |---cst_federation.json
    |---cst_scneario_7.json
|---...

```


## Executables to be Created

## cst_experiment_creator.py
Each scenario defined in the experiment will need to have a scenario created and the "cst_experiment_creator.py" script is responsible for creating those scenarios. The cst_experiment_creator will generate the above file folder sturcture for each scenario defined in the expirement table. After creating this folder structure, cst_experiment_creator will need to load the following files into the metadata database for use when running the experiments: the individual federate configuration JSONs, a federation definition JSON, a federate definition JSON and a scenario-specific defintion JSON. 

Additionally, the "cst_experiment_creator" needs to create a new entry in the "cst scalability test results" document in the metadata database and add the appropriate 

```json
[
    {
        "scenario": 7,
        "number of feds": 10,
        "number of pubs": 100,
        "use endpoints": false,
        "use CST": false,
        "use profiling": false,
        "results": {}
    }
]
```

The "cst_experiment_creator" needs only one execution parameter: the path to the "cst_scalability_experiment" folder. The filenames it needs to load will follow the naming convention and folder structure as defined above and the location in the metadata database each needs to be loaded into is pre-defined by CST.

### cst_scalability_fed.py
This is the generic federate used to stress test CST and it literally does nothing except send and receive data. Specifically, it will publish the current timestep, if enabled send the current timestep value out as a message from its endpoint to the federate next in the federate ring and then receive the same from the federate behind it. In the CST-enable case these published values are logged by the time-series database via logger.py; in the CST-disabled case, the published federate will write out its published values at each timestep to a file.

To increase the efficiency of HELICS when using endpoints, each endpoint should target the endpoint in front of it. This targeting is specified as part of the JSON configuration of the endpoint:

```json
"endpoints": [
    {
      "name": "EV_Controller/EV6",
      "global": true,
      "destinationTarget": "charger/ep"
    }
  ]
```

Psuedocode the the cst_scalability federate is as follow:

```python
read_input_parameters() # argparse library, Trevor has lots of examples
configure_federation(use_cst)
while requested_time < num_timesteps:
    request_next_time()
    get_subscribed_values() # and do nothing with them
    publish_new_values()
    if not use_cst:
        write_publish_values_to_file()
destroy_federate()
```

### cst_scalability_post_processing.py
Collect results and create artifacts (graphs, tables). Scenario defitions should be stored in metadata database

## Execution

All of this should be able to be placed in the CST `run/python` folder where it can be launched either by a local interpreter of the Python container in CST.

All of this should be able to be implemented in a generic Python federate. The federate will accept the following command-line parameters:
1. **Federate index value** - Indicates which HELICS configuration file to load
2. **CST flag** - Indicates whether to use CST or not.
3. **Profiling flag** - Indicates whether to turn on the profiling capability or not.
    

## Data Collection
All of these will be used to create a scalability scenario definition document in the metadata database called "cst scalability test results". The document will be structured as follows:




## Stretch Goals

1. Profiling capability to allow monitoring of the performance capability of the generic federate, likely using a native Python profiling library
2. Profiling capability to allow monitoring of the performance capability of the federation through the CST profiling capability