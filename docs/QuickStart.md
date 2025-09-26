# Quick Start
This page provides the simplest method of installing CoSim Toolbox (CST) and running a few examples. This effectively tests many of the CST APIs and functionality. This set of examples assumes you're running from macOS or Linux or in WSL on Windows. If running Linux, you may have to use `python3` everywhere you see `python` below (depending on your distribution).

## Download and Install CST
This install is for just the APIs and none of the persistent services you may want to use. (For further details see the [full installation page](./Installation.md) )

```shell
$ git clone https://www.github.com/pnnl/cst.git
```

```shell
$ cd cst
```

```shell
$ pip install -r requirements.txt
```

```shell
$ cd src/cosim_toolbox
```

```shell
$ pip install -e .
```

## Verify Installation
There are various ways of confirming the installation was successful

Look for "cst" to be listed as installed by `pip`; this should show the location where the repository was cloned
```shell
$ pip list
```

You can verify that your Python installation is able to `import cosim_toolbox` without error.


```shell
$ python3
>>> import cosim_toolbox
```

## Run the Writer and Reader Example
:::{note}
Before running this or any other examples, set up the environment by sourcing "cosim.env". From the root of the CST repository...

```shell
$ source cosim.env
```

You may see a warning about a Python virtual environment not being set; don't worry about it.
:::

This examples creates data, write it to the data stores (CSV for time-series, JSON for metadata), and then reads it back. No co-simulation is run, just accessing the data stores. These examples are very short and show you the basics of how to CST's backend to write and read data.

From the root of the cloned CST repo, run the time-series CSV example
```shell
$ cd run/data_management
```

```shell
$ python3 example_timeseries_csv.py
```

should produce
```shell
Federate directory not found: test_fed
Federate directory not found: test_fed2
Federate directory not found: test_fed3
scenarios: ['test_scenario']
federates: ['test_fed', 'test_fed2', 'test_fed3']
data_types: ['hdt_boolean', 'hdt_double', 'hdt_double', 'hdt_endpoint', 'hdt_endpoint', 'hdt_integer', 'hdt_integer', 'hdt_string', 'hdt_string']
example_data
                   real_time  sim_time       scenario   federate data_name   data_value receiving_federate receiving_endpoint
2 2025-09-26 14:13:51.828716         0  test_scenario   test_fed     value            1                NaN                NaN
0 2025-09-26 14:13:51.828738         0  test_scenario   test_fed     value          2.0                NaN                NaN
4 2025-09-26 14:13:51.828745         0  test_scenario   test_fed     value         True                NaN                NaN
3 2025-09-26 14:13:51.828748         0  test_scenario   test_fed     value  hello world                NaN                NaN
7 2025-09-26 14:13:51.828753         1  test_scenario   test_fed     value  hello world                NaN                NaN
1 2025-09-26 14:13:51.828756         0  test_scenario   test_fed     value  hello world           receiver  receiver_endpoint
6 2025-09-26 14:13:51.828760         0  test_scenario  test_fed2     value  hello world                NaN                NaN
5 2025-09-26 14:13:51.828763         0  test_scenario  test_fed2     value  hello world           receiver  receiver_endpoint
```

(The "Federate directory not found" messages are indicating this is the first time data is being written for a given federate and are not of concern.)

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
:::{note}
Before running this or any other examples, set up the environment by sourcing "cosim.env". From the root of the CST repository...

```shell
$ source cosim.env
```

You may see a warning about a Python virtual environment not being set; don't worry about it.
:::


There are a number of examples in the "run" folder but the simplest is the "linked_federates". Assuming you are starting from the "data_management" folder from the previous section:
```shell
$ cd ../python/linked_federates
```

The first script we run sets up the federation. Before we run it, we need to ensure that is uses the CSV and JSON backends for time-series data and metadata, respectively. Near the top of the "federate_config.py" file make sure the backends are configured to use "csv" for time-series and "json" for metadata. 

```python
use_meta_db = "json"
use_data_db = "csv"
```

After making those edits, run "federates_config.py" to set up the co-simulation.

```shell
$ python federates_config.py
```

This should print a message to console that the "Configuration files written successfully." In this case, the configuration file produced is a shell script "MyLinkScenario.sh". To run the co-simulation, run this shell script

```shell
$ ./MyLinkScenario.sh
```

This doesn't print anything to console while running and takes a few seconds to complete; once the "helics_broker" process finishes the cosimulation is complete. After it has completed, it will create a few new folders where the time-series data ("data_store") and metadata ("meta_store") are recorded.

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


## **BONUS:** Run an Example Co-Simulation Using CST Databases
Though this is a quickstart guide, it feels wrong not to include an example that uses CST's persistent services to handle the data and metadata. What follows has a few more steps than the previous example due to the installation of the persistent services but will produce a full CST installation. It also demonstrates more of CSTs capabilities handling data using the databases in the persistent services. 

:::{note}
Before running this or any other examples, set up the environment by sourcing "cosim.env". From the root of the CST repository...

```shell
$ source cosim.env
```

You may see a warning about a Python virtual environment not being set; don't worry about it.
:::

### Install Docker
The above example is run using the data backend that writes to local disk. This requires the least effort to get up and running to test the installation. Alternatively, you can use the CST databases as your data store by doing a local installation of said databases and changing your configuration to use the backend that writes to them. To get this up and running, you'll need something to run Docker containers. For in most cases, that means installing Docker; [here's how to do that](https://docs.docker.com/engine/install/).

### Build images
Next, a few Docker images need to be built, using a script in the CST repository. Assuming you're starting from the "linked_federates" folder go to the "docker" folder in scripts and run the "build_cosim_images.sh" script; the build will likely take a few minutes.

```shell
$ cd ../../../scripts/docker
```

```shell
$ ./build-cosim-images.sh
```

### Instantiate the Persistent Services
Once the images have been built, the persistent services can be started. Running the "start_db.sh" script will pull down several images and create several containers from them to build the stack of persistent services.

```shell
$ cd ../stack
```

```shell
$ ./start_db.sh
```

After starting the services, you can confirm they are running.

```shell
$ docker ps
```

You should see something like

```shell
docker ps
CONTAINER ID   IMAGE                                             COMMAND                  CREATED          STATUS                    PORTS                                             NAMES
c0618eaa3795   cosim-jupyter:latest                              "tini -g -- start-no…"   15 seconds ago   Up 14 seconds (healthy)   0.0.0.0:8888->8888/tcp, [::]:8888->8888/tcp       jupyter_notebook
7d55491edbf7   huggingface/mongoku                               "/app/docker-run.sh"     15 seconds ago   Up 14 seconds             0.0.0.0:3100->3100/tcp, [::]:3100->3100/tcp       mongoku
3c86ea43e230   mongo-express                                     "/sbin/tini -- /dock…"   15 seconds ago   Up 14 seconds             0.0.0.0:8081->8081/tcp, [::]:8081->8081/tcp       mongoexpress
7c6108db8960   mongodb/mongodb-community-server:7.0-ubuntu2204   "python3 /usr/local/…"   15 seconds ago   Up 14 seconds             0.0.0.0:27017->27017/tcp, [::]:27017->27017/tcp   mongodb
17758e959487   dpage/pgadmin4:latest                             "/entrypoint.sh"         15 seconds ago   Up 14 seconds             0.0.0.0:80->80/tcp, [::]:80->80/tcp, 443/tcp      pgadmin
034fafe4e87b   grafana/grafana:10.2.4-ubuntu                     "/run.sh"                15 seconds ago   Up 14 seconds             0.0.0.0:3000->3000/tcp, [::]:3000->3000/tcp       grafana
40c64837c76c   timescale/timescaledb:latest-pg12                 "docker-entrypoint.s…"   15 seconds ago   Up 14 seconds (healthy)   0.0.0.0:5432->5432/tcp, [::]:5432->5432/tcp       database
```

### Set-Up and Run Example
The last step before running is to change the back-end used by this example. The previous example wrote to local disk using the CSV and JSON backend; we'll be writing to the Postres and Mongo databases to achieve the same functionality. To make this change, head back to the "linked_federates" folder to edit the "federate_config.py" file to use "postgres" for time-series and "mongo" for metadata.

```shell
$ cd ../../run/python/linked_federates
```

```python
use_meta_db = "mongo"
use_data_db = "postgres"
```

Once that change is made, just run "federates_config.py" to set-up the co-simulation proper and the "MyLinkScenario.sh" to run it. The result from running the script should show it has written configuration files to the Mongo data store successfully (the IP for mongodb will depend on your particular install)


```shell
$ python federates_config.py
...
Writing configuration files to 'mongodb://worker:worker@10.0.1.145:27017'...
Configuration files written successfully.
```


```shell
$ ./MyLinkScenario.sh
```

This doesn't print anything to console while running and takes a few seconds to complete. You can check to see if it has completed by looking to see if a "helics_broker" is running; once it is no longer running the co-simulation has completed.

```shell
$ ps
```

To confirm that data was written correctly to these data stores, run the post-processing script.

```shell
$ python linked_post_processing.py
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



