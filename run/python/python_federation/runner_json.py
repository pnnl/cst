"""
Created on 12/14/2023

Data logger class that defines the basic operations of Python-based logger federate in
Copper.

@author:
mitch.pelton@pnnl.gov
"""

from cosim_toolbox.helicsConfig import Collect
from cosim_toolbox.helicsConfig import HelicsPubGroup
from cosim_toolbox.helicsConfig import HelicsSubGroup
from cosim_toolbox.federation import FederateConfig
from cosim_toolbox.federation import FederationConfig
# from cosim_toolbox.dockerRunner import DockerRunner
from data_management import JSONMetadataManager

fmt = {
    "blank": {"fed": "", "keys": ["", ""], "indices": []},
    "bt": {"fed": "Battery", "keys": ["/", ""], "indices": []},
    "ev": {"fed": "EVehicle", "keys": ["/", ""], "indices": []},
}


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


def get_federation_diction(federation):
    diction = {"federation": {}}
    for name, fed in federation.federates.items():
        diction["federation"][name] = fed.config(
            "HELICS_config", fed.helics.write_json()
        )
    return diction


def write_federation_json(federation, overwrite=False):
    with JSONMetadataManager("./config") as db:
        db.write_federation(federation.federation_name, get_federation_diction(federation), overwrite=overwrite)


def make_scenario_diction(schema_name: str, federation_name: str, start: str, stop: str, docker: bool = False) -> dict:
    """
    Creates a properly formatted CoSimulation Toolbox scenario document
    (dictionary), using the provided inputs.
    """
    return {
        "schema": schema_name,
        "federation": federation_name,
        "start_time": start,
        "stop_time": stop,
        "docker": docker
    }
    
def write_scenario_json(federation, overwrite=False):
    with JSONMetadataManager("./config") as db:
        scenario = make_scenario_diction(
            federation.schema_name,
            federation.federation_name,
            "2023-12-07T15:31:27",
            "2023-12-08T15:31:27",
            federation.docker,
        )
        db.write_scenario(federation.scenario_name, scenario, overwrite=overwrite)


def main():
    remote = False
    with_docker = False
    federation = FederationConfig("MyScenario", "MySchema", "MyFederation", with_docker)

    f1 = federation.add_federate_config(MyFederate1("Battery", period=60))
    f2 = federation.add_federate_config(MyFederate2("EVehicle", period=60))
    federation.define_io()

    if with_docker:
        f1.config("image", "cosim-cst:latest")
    f1.config(
        "command", f"python3 simple_federate.py {f1.name} {federation.scenario_name}"
    )

    if with_docker:
        f2.config("image", "cosim-cst:latest")
    f2.config(
        "command", f"python3 simple_federate.py {f2.name} {federation.scenario_name}"
    )

    # federation.define_scenario("2023-12-07T15:31:27", "2023-12-08T15:31:27")
    write_federation_json(federation, overwrite=True)
    write_scenario_json(federation, overwrite=True)

    # if with_docker:
    #     DockerRunner.define_yaml(federation.scenario_name)
    #     if remote:
    #         DockerRunner.run_remote_yaml(federation.scenario_name)
    #     else:
    #         DockerRunner.run_yaml(federation.scenario_name)
    # else:
    #     DockerRunner.define_sh(federation.scenario_name)


if __name__ == "__main__":
    main()
