# User Guide
Each heading is its own page

## Introduction to CST
- Design Goals
  - Help users built HELICS-based co-simulation without having to learn HELICS APIs
  - Provide an easier way to install common tools used in co-simulations
  - Provide data management tools (config, simulation inputs and outputs)
- Overview of implementation
  - Use of Docker for ease of installation
  - Using existing technologies wherever we could
  - Summarize the functionalities in CST and how they are implemented (similar to the slide deck Trevor used a lot in FY24)


## CST Users
Describe the various types of users/use-cases to help users understand how they think they'll be using CST
- Developer (HELICS "Developer" user) - Making changes to CST itself
  - CST library is installed locally so it can be edited.
  - Persistent services available 
  - Needs to be able to get new Docker containers built with updated code (devops workflow?)
  - Needs to be able to run validation and tests of some kind prior to committing or merging
  - Needs to be able to set up co-simulation runner for split running  (some cosim stuff runs in Dockers and some runs locally)
  - Needs to be able to configure the networking environment and set-up for split running
- Pre-Production User (HELICS "Integrator" - "Modeler" user ) - Developing custom code (_e.g._ controller) that needs to be executed by CST Docker Environment
  - Uses federate.py to create custom code
  - Downloads existing tools via CST Installer as Docker containers
  - Needs a place to put custom code to be run by CST Python
  - Needs a workflow to create a Docker image when tool is ready for primetime
  - Needs a place to put new tool Docker image (image registry) so CST installer can install it
- Production User (HELICS "Modeler" - "Analyst" user) - Just installs tools using CST installer (Docker images) and runs using a pre-defined runner file
  - Needs CST installer to work really well to install everything via Docker images
  - Needs to have good instructions on where to put model files and datasets 
  - Needs to have good instructions on how to launch co-simulation
  - (Not all of this documentation will be generic CST and some will be use-case specific; how will users distribute these instructions? Maybe we can provide a documentation image for them to write and distribute documentation for their use case. Issue added in Jira MSPSA-337)
- Post-Processor (HELICS "Analyst" user) - Data scientists, not a programmer
  - Just needs to install the CST APIs to make accessing the persistent services easy
  - Needs to be able to monitor co-sim progress (Grafana access)
  - Needs to be able to use CST APIs to pull data (presumably from non-local databases)
  - Needs the easiest, smoothest experience of all.  It needs to just work. Something with the level of effort of `pip install cst`

## Installing CST
- Describe installation process for split- vs docker-based-running
- Describe installed environment for split- vs docker-based-running
- Provide installation instructions for each of the CST users above
- Walk-through what the installation looks like on disk and the role of any folders
- Local-only install (persistent services run from containers on local machine) vs distributed install (persistent services are on existing machines)
- 

## Configuring CST
- Database URLs

## Workflows
Provide example workflows by user type. May be very similar or redundant with examples?

## Editing docker-compose to Include a Custom Federate

# Examples
1. Do we have a separate Examples repo like HELICS? (Trevor votes "no".)
2. Do we do like HELICS and have a docs page for each example in RTD OR have a README page in the folder for each example?
- Describing built-in examples
  - Developer user example
  - Post-processing user example
  - Production user example
  - Pre-production user example
- How to run built-in examples (not just launching but looking at results in )
- Walk-through of built-in examples (test cases?)



# Developer Guide
What are the developer tasks?

## Developer workflow
- Make changes
- Run tests
- Format code
- Commit code
- Look for results from automated testing
- If building new images run additional test (maybe?)
- If necessary, manually trigger image builds

## Making a CST Docker image
TODO: Should this be in the User Guide since Pre-Production Users will need to be able to make a Docker image to support Production Users?


## Style Guide
- PEP 8 with the following exceptions
  - (Copy and edit PEP 8 from here: https://github.com/python/peps/blob/main/peps/pep-0008.rst)
- Use of formatter script before committing code
- Formatter extension for VS Code?

# References

## API reference
Auto-generated
