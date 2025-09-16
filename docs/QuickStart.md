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
There are a number of examples in the "run" folder but the simplest is the "linked_federates". Assuming you are starting from the "data_management" folder from the previous section:
```shell
$ python ../python/linked_federates
```

The first script we run sets up the federation. Near the top of the file make sure the backends are configured to use "csv" for time-series and "json" for metadata

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

This doesn't print anything to console but will create a few new folders where the time-series data ("data_store") and metadata ("meta_store") are recorded.

To confirm that data was written correctly to these data stores, run the post-processing script.

```shell
$ python post_processing.py
```
