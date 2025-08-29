"""
Created on 12/14/2023
Example runner script for defining and deploying a co-simulation federation.

This script demonstrates how to:
1. Define a federation configuration using the FederationConfig class.
2. Generate the necessary JSON configuration files using the new
   data_management API.
3. Generate the deployment artifacts (docker-compose.yaml or a .sh script)
   using the DockerRunner class.
@author:
mitch.pelton@pnnl.gov
"""

# --- Core Co-simulation Toolbox Imports ---
import cosim_toolbox as env
from cosim_toolbox.helicsConfig import Collect, HelicsPubGroup, HelicsSubGroup
from cosim_toolbox.federation import FederateConfig, FederationConfig
from cosim_toolbox.dockerRunner import DockerRunner

# --- New API Import for Writing Metadata ---
from data_management.factories import create_metadata_manager

# Helper dictionary for defining publications and subscriptions
fmt = {
    "blank": {"fed": "", "keys": ["", ""], "indices": []},
    "bt": {"fed": "Battery", "keys": ["/", ""], "indices": []},
    "ev": {"fed": "EVehicle", "keys": ["/", ""], "indices": []},
}

# --- Custom Federate Definitions ---
# These classes define the specific components of our federation.
# They inherit from FederateConfig to define their I/O and properties.


class MyFederate1(FederateConfig):
    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)
        self.outputs["current1"] = HelicsPubGroup(
            "EV_current", "double", fmt["bt"], unit="A", globl=True
        )
        self.inputs["voltage1"] = HelicsSubGroup(
            "EV_voltage", "double", fmt["ev"], unit="V"
        )
        self.config("federate_type", "value")
        self.helics.collect(Collect.NO)


class MyFederate2(FederateConfig):
    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)
        self.outputs["voltage1"] = HelicsPubGroup(
            "EV_voltage", "double", fmt["ev"], unit="V", globl=True
        )
        self.inputs["current1"] = HelicsSubGroup(
            "EV_current", "double", fmt["bt"], unit="A"
        )
        self.config("federate_type", "value")
        self.helics.collect(Collect.NO)


def main():
    # --- Control Flags ---
    # Toggle these flags to control the output.
    remote = False
    with_docker = False

    # --- 1. Define the Federation Configuration ---
    # Use the FederationConfig class to set up the overall federation.
    federation = FederationConfig("MyScenario", "MySchema", "MyFederation", with_docker)

    # Add the specific federate configurations to the federation object.
    f1 = federation.add_federate_config(MyFederate1("Battery", period=60))
    f2 = federation.add_federate_config(MyFederate2("EVehicle", period=60))

    # This crucial step links the publications and subscriptions together.
    federation.define_io()

    # Define the commands and images needed for deployment.
    if with_docker:
        f1.config("image", "cosim-cst:latest")
        f2.config("image", "cosim-cst:latest")

    f1.config(
        "command", f"python3 simple_federate.py {f1.name} {federation.scenario_name}"
    )
    f2.config(
        "command", f"python3 simple_federate.py {f2.name} {federation.scenario_name}"
    )

    # --- 2. Generate and Write Configuration Files ---
    # This block replaces the old `federation.define_scenario()` call.
    # It demonstrates the new, decoupled workflow.

    # Get the configuration dictionaries from the FederationConfig object.
    fed_doc = federation.get_federation_document()
    scen_doc = federation.get_scenario_document(
        start_time="2023-12-07T15:31:27", stop_time="2023-12-08T15:31:27"
    )

    # Use the new data_management API to write the configurations to disk.
    # Here, we use a JSON backend, but this could easily be switched to 'mongo'.
    with create_metadata_manager(**env.cst_default_mongo_setup) as mgr:
        print(f"Writing configuration files to '{mgr.location}'...")
        mgr.write_federation(federation.federation_name, fed_doc, overwrite=True)
        mgr.write_scenario(federation.scenario_name, scen_doc, overwrite=True)
        print("Configuration files written successfully.")

    # --- 3. Generate Deployment Artifacts ---
    # Use the DockerRunner class to create the .yaml or .sh file.
    # We pass the configuration dictionaries directly to the new methods.
    if with_docker:
        print(f"Generating Docker Compose file: {federation.scenario_name}.yaml")
        DockerRunner.define_yaml(federation.scenario_name, scen_doc, fed_doc)

        # Optionally, run the docker-compose file.
        if remote:
            DockerRunner.run_remote_yaml(federation.scenario_name)
        else:
            DockerRunner.run_yaml(federation.scenario_name)
    else:
        print(f"Generating shell script: {federation.scenario_name}.sh")
        DockerRunner.define_sh(federation.scenario_name, scen_doc, fed_doc)

    print("Runner script finished.")


if __name__ == "__main__":
    main()
