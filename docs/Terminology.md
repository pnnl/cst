# Terminology
CoSim Toolbox (CST) has defined a data model that provides a consistent terminology throughout the APIs (regardless of the underlying tool) and provides a means of thinking more concretely about the work being planned. The following are the terms of art used in CST:

TODO: Add diagram?

TODO: double-check that the information presented here is correct

TODO: double-check that the information here is comprehensive enough

## "analysis"
This is the highest level abstraction when thinking about the work being conducted in the co-simulation. The analysis describes the goals of the work and what comparisons are being made in the study. The concept of "analysis" does not manifest much in the APIs but is useful as parent concept to contain all of the others.

## "scenario"
A "scenario" is a specific set analysis parameters that are defined to create a single analysis case. The goals of the analysis are revealed through the comparison between one or more scenarios. For example, the analysis may call out that a comparison needs to be made betwen a particular model with and without EVs; this requires the definition of two scenarios. The definition of the scenarios is stored in the configuration database and is used by the CST APIs to configure federates. This information is also useful when analyzying co-simulation output data to see the values of the analysis parameters when creating graphs, tables, and charts in post-processing. Scenario data can also be extended to include information beyond analysis parameters directly used in the configuration of the co-simulation. Data in the time-series database uses the "scenario" value as a key parameter when storing the data.

## "federate"
A "federate" is an instance of a simulation tool with a specific model and/or data set. For example, there may be a tool that simulates a single neighborhood in the power system. Every time this simulator is instantiated in the co-simulation and a different neighborhood is modeled, a new federate is defined with a unique name. In HELICS, each federate needs specific configuration information to join the co-simulation as defined by the analysis. Data in the time-series database uses the "federate" value as a key parameter when storing the data.

## "federation"
Each scenario defines a set of federates to be used to model all the is required for that scenario and this collection of the federates is called the "federation". All federates in the federation are defined in the configuration database. Generally, there is a strong overlap in the federation definition between scenarios in a given analysis. 

## Note on Terminology
The definitions presented here are primarily used when constructing the databases and the CST APIs developed to access them. Using any unqiue combination "analysis" and "scenario" will guarantee data and metadata is not overwritten from previous co-simulation runs. Additionally, it is possible that the configuration metadata stored in the database is intended to be used across multiple scenarios and analysis.