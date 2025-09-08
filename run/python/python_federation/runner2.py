"""
Created on 12/14/2023
Example runner script for defining and deploying a co-simulation federation.

This script demonstrates how to:
1. Define a federation configuration using the FederationConfig class.
2. Generate the necessary JSON configuration files using the new
   database management system (dbms) API.
3. Generate the deployment artifacts (docker-compose.yaml or a .sh script)
   using the DockerRunner class.
@author:
mitch.pelton@pnnl.gov
"""

from cosim_toolbox.helicsConfig import Collect, HelicsPubGroup, HelicsSubGroup
from cosim_toolbox.federation import FederateConfig, FederationConfig
from cosim_toolbox.dockerRunner import DockerRunner

# Helper dictionary for defining publications and subscriptions
fmt = {
    "bt": {"from_fed": "Battery",
           "keys": ["", ""],
           "indices": []},
    "ev": {"output_fed": True,
           "from_fed": "Battery",
           "to_fed": "EVehicle",
           "keys": ["", ""],
           "indices": []},
    "ev1": {"from_fed": "EVehicle",
            "keys": ["", ""],
            "indices": []},
    "bt1": {"output_fed": True,
            "from_fed": "EVehicle",
            "to_fed": "Battery",
            "keys": ["", ""],
            "indices": []},
}

# --- Custom Federate Definitions ---
# These classes define the specific components of our federation.
# They inherit from FederateConfig to define their I/O and properties.

class MyFederate1(FederateConfig):
    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)
        self.outputs["current1"] = HelicsPubGroup("EV_current", "double", fmt["bt"], unit="A", globl=True)
        self.inputs["voltage1"] = HelicsSubGroup("EV_voltage", "double", fmt["ev"], unit="V")
        self.config("federate_type", "value")
        self.helics.collect(Collect.NO)

class MyFederate2(FederateConfig):
    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)
        self.outputs["voltage1"] = HelicsPubGroup("EV_voltage", "double", fmt["ev1"], unit="V", globl=True)
        self.inputs["current1"] = HelicsSubGroup("EV_current", "double", fmt["bt1"], unit="A")

        self.config("federate_type", "value")
        self.helics.collect(Collect.NO)

def define_format():
    # --- Control Flags ---
    # Toggle these flags to control the output.
    remote = False
    with_docker = False

    # --- 1. Define the Federation Configuration ---
    # Use the FederationConfig class to set up the overall federation.
    federation = FederationConfig("MyScenario", "MyAnalysis", "MyFederation")

    # Add the specific federate configurations to the federation object.
    f1 = federation.add_federate_config(MyFederate1("Battery", period=60))
    f2 = federation.add_federate_config(MyFederate2("EVehicle", period=60))

    # This crucial step links the publications and subscriptions together.
    federation.define_io()

    # Define the commands and images needed for deployment.
    if with_docker:
        f1.config("image", "cosim-cst:latest")
    f1.config("command", f"python3 simple_federate.py {f1.name} {federation.scenario_name}")

    if with_docker:
        f2.config("image", "cosim-cst:latest")
    f2.config("command", f"python3 simple_federate.py {f2.name} {federation.scenario_name}")

    # --- 2. Generate and Write Configuration Files ---
    federation.write_config("2023-12-07T15:31:27", "2023-12-08T15:31:27")

    # --- 3. Generate Deployment Artifacts ---
    # Use the DockerRunner class to create the .yaml or .sh file.
    # We pass the configuration dictionaries directly to the new methods.
    if with_docker:
        DockerRunner.define_yaml(federation.scenario_name)
        if remote:
            DockerRunner.run_remote_yaml(federation.scenario_name)
        else:
            DockerRunner.run_yaml(federation.scenario_name)
    else:
        DockerRunner.define_sh(federation.scenario_name)

if __name__ == "__main__":
    define_format()