# Quick Start
This page provides the simplest method of installing CoSim Toolbox (CST) and running an example

## Download and Install CST
This install is for just the APIs and none of the persistent services you may want to use. (For further details see the [full installation page](./Installation.md) )

```shell
$ git clone https://www.github.com/pnnl/cst/cst.git
```

```shell
$ cd cst
```

```shell
$ pip install -r requirements.txt
```

```shell
$ cd src
```

```shell
$ pip install .
```

## Verify Installation
There are various ways of confirming the installation was successful

Look for "cst" to be listed as installed by `pip`; this should show the location where the repository was cloned
```shell
$ pip list
```

You can verify that your Python installation is able to `import cosim_toolbox` without error.
```shell
$ cd ../
```

```shell
$ python
>>> import cosim_toolbox
```

## Run the Writer and Reader Example
Before running this or any other examples, set up the environment by sourcing "cosim.env". From the root of the CST repository...

```shell
$ source cosim.env
```

These examples create data, write them to the data stores (CSV for time-series, JSON for metadata), and then reads them back. No co-simulation is run, just accessing the data stores. These examples are very short and show you the basics of how to CST's backend to write. Here's links to the source code for writing and reading to the [time-series CSV data store]() and the [metadata JSON data store](). 

From the root of the cloned CST repo, run the time-series CSV example
```shell
$ cd run/data_management
```

```shell
$ python example_timeseries_csv.py
```

should produce
```shell
Federate directory not found: test_fed
scenarios: ['test_scenario']
federates: ['test_fed']
data_types: ['hdt_boolean', 'hdt_double', 'hdt_integer', 'hdt_string']
example_data
                   real_time  sim_time       scenario  federate data_name   data_value
0 2025-09-12 12:34:43.492862         0  test_scenario  test_fed     value          2.0
1 2025-09-12 12:34:43.492854         0  test_scenario  test_fed     value            1
2 2025-09-12 12:34:43.492866         0  test_scenario  test_fed     value  hello world
3 2025-09-12 12:34:43.492865         0  test_scenario  test_fed     value         True
```

Similarly, run the metadata example

```shell
$ python example_metadata_json.py
```

should produce
```shell
scenarios: ['example_scenario']
federations: []
{'analysis': 'example_analysis', 'federation': 'example_federation', 'start_time': 0.0, 'stop_time': 10.0, 'docker': False}
```

## Run an Example Co-Simulation
(Before running this or any other examples, set up the environment by sourcing "cosim.env". From the root of the CST repository...)

```shell
$ source cosim.env
```


There are a number of examples in the "run" folder but the simplest is the "linked_federates". Assuming you are starting from the "data_management" folder from the previous section:
```shell
$ python ../python/linked_federates
```

The first script we run sets up the federation. Before we run it, we need to ensure that is uses the CSV and JSON backends for time-series data and metadata, respectively. Near the top of the "federate_config.py" file make sure the backends are configured to use "csv" for time-series and "json" for metadata

```python
use_meta_db = "json"
use_data_db = "csv"
```

```shell
$ python federate_config.py
```

This should print a message to console that the "Configuration files written successfully." In this case, the configuration file produced is a shell script "MyLinkScenario.sh". To run the co-simulation, run this shell script

```shell
$ ./MyLinkScenario.sh
```

This doesn't print anything to console while running and takes a few seconds to complete. After it has completed, it will create a few new folders where the time-series data ("data_store") and metadata ("meta_store") are recorded.

To confirm that data was written correctly to these data stores, run the post-processing script.

```shell
$ python link_post_processing.py
```

You should get the following results printed to console:

```shell
Metadata scenario name: MyLinkScenario
Metadata federation name: MyLinkFederation
Metadata analysis name: MyLinkAnalysis
Metadata federates list: ['Battery', 'EVehicle']
Time-series scenarios list: ['MyLinkScenario']
Time-series federates list: ['Battery', 'EVehicle']
Time-series data types list: ['hdt_boolean', 'hdt_complex', 'hdt_double', 'hdt_endpoint', 'hdt_endpoint', 'hdt_string']
            real_time  sim_time        scenario federate         data_name receiving_federate receiving_endpoint   data_value
0 2023-12-07 15:31:57      30.0  MyLinkScenario  Battery  Battery/current1           EVehicle  EVehicle/voltage1          2.0
1 2023-12-07 15:31:57      30.0  MyLinkScenario  Battery  Battery/current5                NaN                NaN  (-1e+49+1j)
2 2023-12-07 15:31:57      30.0  MyLinkScenario  Battery          current4                NaN                NaN            0
3 2023-12-07 15:31:57      30.0  MyLinkScenario  Battery   Battery/current                NaN                NaN          0.0
4 2023-12-07 15:31:57      30.0  MyLinkScenario  Battery          current3                NaN                NaN        False
```

## **BONUS** Run an Example Co-Simulation Using CST Databases
(Before running this or any other examples, set up the environment by sourcing "cosim.env". From the root of the CST repository...)

```shell
$ source cosim.env
```

The above example is run using the data backend that writes to local disk. This requires the least effort to get up and running to test the installation. Alternatively, you can use the CST databases as your data store by doing a local installation of said databases and changing your configuration to use the backend that writes to them. To get this up and running, you'll need something to run Docker containers. For in most cases, that means installing Docker; [here's how to do that](https://docs.docker.com/engine/install/).

Once you've got that installed and running, you can instantate the persistent services through "docker-compose". Assuming you're starting from the "linked_federates" folder...

```shell
$ cd ../../../scripts/stack
```


```shell
$ 
```

build docker images if necessary in docker/build

run start_db.sh - pulls down images

confirm with docker ps

Change federates_config.py to use "mongo" and "postgres"

Run example with python linked_federates.py

Check progress of co-simulation by looking at databases
PGAdmin check outs postgres
IP:80



