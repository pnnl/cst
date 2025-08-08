# Configuration API v2 Design

## API Purpose
Creationand management of the data exchange paths in a HELIC co-simulation is a relatively time-intensive part of successfully running a co-simulation. As the number of federates and/or the number of interface points between the federates increase, creating a number number of data transfers that need to be defined and verfified. For all but the simplest federations, the number of data exchanges is generally defined in a programmatic way (rather than hand-crafted). The configuration APIs in CoSim Toolbox (CST) are intended to provide a systemic means of defining the data transfers that are needed for a given federation and verify that they have been correctly specified.

## Federation Class
The federation class holds the configuration information for the entire federation, including the HELICS configuration information. There are several key parameters

### `data_transfers`
`data_transfers` is the attribute used to hold the generated list of outputs and inputs for the entire federation and is represented as a list of DataTransfer objects. Each of these objects specifies the transfer group name, the output and input federate name, and the output and input HELICS configuration object.

The data transfer is fully specified in pairs of outputs (HELICS publications) and inputs (HELICS inputs). Both of these entities in HELICS are named which allows either the publication to specify where to send its output or the input to specify which output it is targeting. For simplicity, in CST we specify the destination of the data from the publication using the HELICS "targets" parameter. Note that this parameter can be a list, thus allowing multiple HELICS inputs to be fed from a single HELICS publication.

### `transfer topology`
(**TODO** _Lower priortity attribute and corresponding API to generate this attribute._)
The `transfer topology` attribute holds a networkx object of the data transfer topology. The graph is built calling the `create_transfer_topology()` method of this class. This method traverses the `data_transfer` attribute and builds the data transfer topology, showing which federates are providing which information to each other. By default, this topology is built using the data transfer groups to reduced the number of edges in the graph; the API takes a flag to disable this aggregation and build the model by publication-input pairs.

### `federate_general_configs`
The `federate_general_configs` is a list of `HELICSFederateGeneralConfig` objects. These objects hold all the HELICS configuration parameters that are unrelated to data transfers (_e.g._ federate name, core type, uninterruptible flag). These parameters apply to the federate as a whole and thus are defined independently. Elements are added to this list with the `add_federate_config()` API of this class.

### `federate_configs`
The `federate_configs` parameter is a list of the `HELICSFederateConfig` objects used to define the federation. (This is distinct from the `Federate` class which is an implementation of a generic HELICS federate with minimal coding and knowledge of the HELICS APIs.) T