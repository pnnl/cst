# Scalability Testing 

## Motivation

E-COMP leadership has prioritized scalability testing for CST as a "no-regrets" activity that can be started early in FY25. The purposes of this activity are as follows:

1. Demonstrate the scalability of CST to at least 100 federates. Though this may not be in doubt to us close to the software, having it demonstrated bring credibility to the platform and creates a talking point for the software.
2. Identify low-performing code in CoSimulation Toolbox for improvement and make improvements where possible.

To this end, we will be building and conducting scalability testing in Oct FY25 to determine the impact of using CST when performing a HELICS-based co-simulation.

## Experiment Requirements

1. Easily scalable to an arbitrarily large number of federates.
2. Uses federate.py
3. Uses metadata database and time-series database 
4. Produces sufficient data to exercise the time-series database via logger.py
5. Federation execution time instrumentation to measure execution time under various conditions
6. Needs to be able to be run without CST as baseline
    - Same number of federates and same federation topology
    - Uses federate.py (Debatable; Trevor speculates there's not a lot of inefficiency there)
    - No Docker
    - Writing to file rather than database
    - Local configuration JSON files, no configuration via APIs
    - Use the same version of Python locally as in the Docker environment



## Experiment Design

The CST scalability experiment will have the following parameters and values:

1. Number of federates: [10, 100, 1000]
2. Number of pubs and subs per federate: [1, 10, 100]
3. Use of endpoints: [true, false]
4. Use of CST: [true, false]
5. Use of profiling: [true, false]

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
To run a given scenario, the following files will need to be created on disk (_x_ is the number of federates and _m_ is the scenario test designator)

1. **federate_x_config.json** - HELICS configuration JSON for a given federate
2. **cst_federate.json** - Federate defintion information used by CST
3. **cst_federation.json** - Federation definition information used by CST
4. **cst_scenario_m.json** - Scenario definition information used by CST
5. **cst_scenario_m_runner.py** - Launch script for the execution of this scenario

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
    |---cst_scenario_7.json
    |---cst_scenario_7_runner.py
    |---cst_scalability_fed.py
    |---cst_results_validator.py
    |---outputs
        |---timing_results.csv
        |---cst_scalability_fed_1_output.csv
        |---cst_scalability_fed_2_output.csv
        |---cst_scalability_fed_3_output.csv
        ...
|---...

```

"cst_scalability_fed.py" and "cst_results_validtor.py" will be copied into each folder from elsewhere in the CST repository by the same script that creates these file structures. The "outputs" folder will need to be created but the contents of that folder will be created by the individual federates and are shown here for reference.


## Executables to be Created

### cst_experiment_creator.py
Each scenario defined in the experiment will need to have a scenario created and the "cst_experiment_creator.py" script is responsible for creating the files, folder structure, and database entries necessary to run all scenarios in the experiment. cst_experiment_creator will generate the above file folder structure for each scenario defined in the expirement table. After creating this folder structure, cst_experiment_creator will need to load the following files into the metadata database for use when running the experiments: the individual federate configuration JSONs, a federation definition JSON, a federate definition JSON and a scenario-specific defintion JSON. (The federate definition json may possibly need to be loaded once and used across all experiment scenarios.)

Additionally, cst_experiment_creator needs to create an entry in the "cst scalability test results" document in the metadata database for each scenario. An example of this for Scenario 7 is shown below.

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

cst_experiment_creator needs only one execution parameter: the path to the "cst_scalability_experiment" folder on disk. The filenames it needs to load will follow the naming convention and folder structure as defined above and the location in the metadata database each needs to be loaded into is pre-defined by CST.

### cst_scalability_fed.py
This is the generic federate used to stress test CST and it literally does nothing except send and receive data via HELICS. Specifically, it will receive data from the federate behind it in the ring on its subscriptions and endpoint (if applicable for the given scenario). It will also use its defined publication(s) and endpoint (if applicable for the given scenario) to send the current timestep value to the federate next in the ring.  In the CST-enable case these published values are logged by the time-series database via logger.py; in the CST-disabled case, each federate will will log the values it receives to an output CSV in the "outputs" folder of the previously defined file structure. The CSV will be of the following format:

```
sim time, real time, pub 1, pub 2, pub 3, ...., pub n
1, <<datetime string>>, 0, 0, 0, ...., 0
```

To increase the efficiency of HELICS when using endpoints, each endpoint should target the endpoint in front of it. This targeting is specified as part of the JSON configuration of the endpoint:

```json
"endpoints": [
    {
      "name": "ep",
      "global": false,
      "destination_target": "federate_name_next_in_ring/ep"
    }
  ]
```

The command line arguments for cst_scalability_fed are as follows:

1. **Federate index value** - which position in the federate ring this federate will take on
2. **CST flag** - Indicates whether to use CST or not and impact various federate operations such as configuration and output logging.
3. **Profiling flag** - Indicates whether to turn on the profiling capability or not.

Psuedocode for cst_scalability_fed is as follow:

```python
read_input_parameters() # argparse library; Trevor has lots of examples
configure_federation(use_cst_flag)
while requested_time < num_timesteps:
    request_next_time()
    get_subscribed_values()
    if not use_cst_flag:
        write_received_values_to_file()
    publish_new_values()
destroy_federate()
```

### cst_scenario_m_runner.sh
This runner script will be used by either CST to launch the experiment or when launching the federation when running in the native environment. The contents of the script will be similar between these two cases but not identical. In particular, cst_scalability_fed needs to know how it is being run for various activities such as configuring itself (via the metadata database or a local JSON file) or correctly logging its output data.

This runner script is also responsible for recording the execution time information and pushing it into the "results" object of the scenario definition in the metadata database. That object should be structured as follows:

```json
"results": {
    "runtime": 1234
}
```

If later more details profiling information is added, the object structure will be expanded.

### cst_results_validator.py
Though the data exchanged in the co-simulation is just created for test purposes, we do need to validate that the data exchanges took place as expected. To do this, the outputs generated in each scenario need to be checked for completeness. That is, at every time step, for every publication and endpoint, for every federate, the data written to the database or output file needs to be checked. Due to the design of the federation and the data payloads, the time the data was sent will be one integer greater than the data itself. 

The folder structure itself will indicate which scenario cst_results_validator needs to validate and the specific scenario defintion can be pulled from the metadata database (_e.g._ number of federates, number of publications). Once the validation is completed, the "validated" boolean can be set in the "results" object for this scenario in the metadata database as shown below:

```json
"results": {
    "runtime": 1234,
    "validated": true
}
```


### cst_scalability_post_processing.py
This script is responsible for creating the artifacts of the analysis; in this case, the graphs showing the impact of the various factors. Before creating the graphs, though, the "validated" flag needs to be checked to ensure that the scenario run executed succesffully. If not all outputs have been validated then a (non-terminal) error should be thrown and that data omitted from the appropriate graphs.


 Once all scenario results have been confirmed validate, the following graphs will need to be created:


- Use endpoints = false
 - Pub count = 1, **Graph:** x-axis: Fed count, y-axis: delta in runtime between [1, 19], [2, 20], and [3, 21]
 - Pub count = 10 **Graph:** x-axis: Fed count, y-axis: delta in runtime between [4, 22], [5, 23], and [6, 24]
 - Pub count = 100 **Graph:** x-axis: Fed count, y-axis: delta in runtime between [7, 25], [8, 26], and [9, 27]
- Use endpoints = true
 - Pub count = 1 **Graph:** x-axis: Fed count, y-axis: delta in runtime between [10, 28], [11, 29], and [12, 30]
 - Pub count = 10 **Graph:** x-axis: Fed count, y-axis: delta in runtime between [13, 31], [14, 32], and [15, 33]
 - Pub count = 100 **Graph:** x-axis: Fed count, y-axis: delta in runtime between [16, 34], [17, 35], and [18, 36]



## Execution
The "cst_scalability_experiment" produced by cst_experiment_creator.py should be placed in the CST "run/python" folder where it can be launched either by a local interpreter of the Python container in CST.

For scenarios where the data is logged to file and 1000 federates are running simultaneously, it may be necessary to adjust the number of open files the OS supports. In Linux this is a configurable system variable.

The execution order for the entire experiment will be as follows:

```sh
cst_experiment_creator.py # Creates the folder structure for all the scenarios and creates necessary documents in the metadata database
cst_scenario_m_runner.sh # Execute the runner for each scenario.
cst_results_validator.py # After all scenarios are complete, validate their results
cst_scalability_post_processing.py # After results have been validated, create the results graphs
```



## Stretch Goals

1. Profiling capability to allow monitoring of the performance capability of the generic federate, likely using a native Python profiling library
2. Profiling capability to allow monitoring of the performance capability of the federation through the CST profiling capability