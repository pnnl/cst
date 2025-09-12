# Quick Start
This page provides the simplest method of installing CoSim Toolbox (CST) and running an example

## Download and Install CST
This install is for just the APIs and none of the persistent services you may want to use. (For further details see the [full installation page](./Installation.md) )

```shell
$ git clone https://www.github.com/pnnl/cst/cst.git
```

```shell
$ cd ./cst/src/
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

You can verify that your Python installation is able to import cst.

```shell
$ python
>>> import cst
```

## Run the Writer and Reader Example
These examples create data, write them to the data stores (CSV for time-series, JSON for metadata), and then reads them back. No co-simulation is run, just accessing the data stores. These examples are very short and show you the basics of how to CST's backend to write. Here's links to the source code for writing and reading to the [time-series CSV data store]() and the [metadata JSON data store](). 

From the root of the cloned CST repo, run the time-series CSV example
```shell
$ python ./run/data_management/example_timeseries_csv.py
```

should produce
```shell
scenarios:
federates:
data_types:
analysis name:
```

Similarly, run the metadata example

```shell
$ python ./run/data_management/example_metadata_json.py
```

should produce
```shell
scenarios:
federations:
```

## Run an Example Co-Simulation
