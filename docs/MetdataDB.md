# Metadata (Configuration) Management
CST provides the metadata database as a centralized location for storing metadata related to the analysis. the database being used for this is MongoDB which can be thought of storing data as JSONs or Python dictionaries. This allows non-tabular but structured data to be stored and easily retrieved by any simulation entity or researcher (tabular data is stored in the time-series database). This allows federates to pull down their configuration information (rather than relying on a local configuration file) or a researcher that is making a comparison across scenarios to pull down particular parameter values when performing post-processing.

The CST metadata database is a MongoDB instance with 

CST has two sets of JSONs that it uses when building a co-simulation, "federations" and "scenarios". It is the responsibilty of the analysis team to create these and upload them to the metadata database prior to trying to run the co-simulation. This document is intended to help describe how the metadata database works and how these required JSONs are structured.


## CST Data Structure

### "federations" 
**TODO** - Get rid of key names with underscores

The "federations" collection holds the definitions for a given federation. 

Each JSON in "federations" uses the federate name as the key and the provides the configuration information for that federate using the following structure with the required elements shown.

```json
{
    "<federate_name>": {
        "logger": true,
        "image": "cosim-python:latest",
        "command": "python3 example_federate.py",
        "federate_type": "value",
        "time_step": 120,
        "<federate custom key>": "<federate custom value>",
        "HELICS_config": {
            "<HELICS configuration keys>": "<HELICS configuration values>" 
        }
    },
    "<federation custom key>": "<federation custom value>"
}
```

#### `logger`
**TODO** - Need clarification on this. "federate.py" is showing the use of "tags" which I'm not seeing the in the configuration saved in Mongo.

Boolean to indicate whether this federate should have its outputs collected by CST's "Logger" federate.

#### `image`
For federates that use a Docker image to install a simualtion tool, this defines which image to use.

This information is not used if a Docker image is not used to instantiate a federate and can be left as an empty string (`""`) if this is the case.

#### `command`
Command to call to launch the federate. If using a Docker image this is the command that runs once inside the container created from the previously specified image. If not running inside a Docker container, this is the command that will be called on the hosts command line.

#### `federate_type`
Used by the CST Federate class to instantiate the correct type of HELICS federate. The string specified here must be one of the following:

- "value"
- "message"
- "combo"

See the [HELICS documentation](https://docs.helics.org/en/latest/user-guide/fundamental_topics/federates.html) for further details.

#### `time_step` 
For federates that advance through time regularly, this is the default time-step size that is used by CST's Federate class. If this is not an integer multiple of `period` in the `HELICS_config` object HELICS will throw warning messages during runtime. 

#### `<federate custom key>`
Any custom configuration value needed by the federate can be added without disrupting CSTs use of the JSON.

#### `HELICS_config`
This is the HELICS configuration JSON and is directly stored here. Any content in this object needs to conform to what HELICS needs to create a federate. [Comprehensive documentation on the HELICS configuration JSON](https://docs.helics.org/en/latest/references/configuration_options_reference.html) can be found in HELICS documentation.

### "scenarios"
**TODO** - Get rid of key names with underscores

As [previously defined](./Terminology.md#scenario), a scenario is a set of simulation parameter values that is named. Typically a given analysis will have multiple scenarios who's outputs are compared to reach a meaningful conclusion. The "scenarios" collection stores JSONs that hold any parameters that are used to define a given scenario as a whole. Like the "federations" collection, there are a few required values shown below but any additional custom value can be added without disrupting CST's use of the JSON.

#### `analysis`
This is the name of the Postgres schmea used in the time-series database and is used when configuring said database.

#### `federation`
This is the name of the federation and is used to access the configuration information for this particular federation stored in the "federations" object here in the metadata database.

#### `start_time`
Start time of the simulation specified using ISO 8601.

#### `stop_time`
Stop time of the simulation specified using ISO 8601.

#### `docker`
Setting to `true` will generation a docker-compose.yaml that will be used in launching any docker images used to launch simulation tools used by any of the federates. If any federate needs to use a Docker image to run, this should be set to `true`.

#### `cst_007`
`cst_007`  is a reserved word that is used to store the name of the JSON to allow for easier access (rather than using the MongoDB `_id`). When you write the JSON to the metadata database and give it a name, this is where that value is stored. When you retrieve a JSON from the metadata database by name, this is the field that is searched for. Generally, you shouldn't need to read or write this field directly.

## Using CST's metadata database
 There is comprehensive documentation on the metadata database API provided by CST in the API documentation section (**TODO** add link to API documentation) and we're not going to replicate it all here. Most database operations can be thought of using the CRUD acronymn (create, read, update, delete) and the CST APIs support these operations. 

 Virtually all of the required CST metadata that is stored in these databases only needs to be defined and written in once. For example, if you're conducting a study evaluating the impact on distribution system voltage as EV penetration increases, you may define five scenarios where the EV penetration is 0%, 20%, 40%, 60%, and 80%. Once you've defined the parameters for these scenarios and written them to the metadata database, they don't need to be re-written every time you run one of the scenarios (unless a parameter value changes).  Though CST provides some APIs to help define the configuration (**TODO** - add link to documentation), it still takes some effort to get all the details right. The good news is once you have them done, you can push them up into the metadata database and then anybody who wants to run any of the scenarios or look at data from the scenarios has access to that configuration information.

 For those  

