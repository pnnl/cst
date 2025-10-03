# CoSim Toolbox Overview

CoSim Toolbox (CST) is a suite of Dockerized tools and libraries that make it easier to build, run, and analyze HELICS-based co-simulations. Some of these applications are web-based services (_e.g._ databases for storing configuration and simulation data) and some of these are simulation tools themselves. Additionally, CST provides a Python HELICS federate class that makes writing a HELICs federate easier and provides access to some CST functionality with no additional coding.

## Major Features
CoSim Toolbox has the following key features:

- **Cross-platform installation via Docker** - All CST-supported tools and libraries are available via Docker images. This allows HELICS co-simulations to be run on Linux, macOS, and Windows and makes for an easy installation. Additionally, any simulator with HELICS support can join a CST co-simulation, even if it is not able to run in Docker.
- **Co-Simulation Time-Series Data Logging** - CST has a configurable data logger that collects any user-specified data provided via HELICS into a database. This makes data collection from the co-simulation simple and through the use of CST-provided APIs, make accessing the logged data possible by any user that can reach the database without having to learn a query language.
- **Co-Simulation Configuration Management** - To assist to managing the configuration of the federates and the co-simulation in general, CST provides a centralized database and a data model for storing and retrieving configuration information. Federates that use the CST federate class are able to retrieve their HELICS configuration directly from the database. CST also provides APIs for reading and writing to this database without learning a database query language.
- **CST federate class** - CST provides a Python Federate class that uses both a template for how a basic HELICS federate operates and incorporates the HELICS API calls so that for basic federates, no knowledge of HELICS APIs are required to write the 'federate'. And being class-based, users are able to subclass and overload any of the methods to provide specific functionality not implemented in the basic Federate class.

The time-series data logging, configuration management, and monitoring are considered "persistent services" that can be installed and run locally on the user's computer via Docker or can be installed in a centralized location for a group or team to use collectively. The former can be useful for initial development or where data is meant to be kept private. The latter is useful when working on a team with centralized computation infrastructure for both data-sharing or co-simulation performance reasons.

## Documentation
Full documentation is available on [ReadTheDocs](./docs/index.md).


## Trying Out CST

The easiest way to install and try out CST is using walking through our [Quick Start page](./docs/QuickStart.md).