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
from cosim_toolbox.dockerRunner import DockerRunner

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

def  define_format():
    remote = False
    with_docker = False
    federation = FederationConfig("MyScenario", "MySchema", "MyFederation", with_docker)

    f1 = federation.add_federate_config(MyFederate1("Battery", period=60))
    f2 = federation.add_federate_config(MyFederate2("EVehicle", period=60))
    federation.define_io()

    if with_docker:
        f1.config("image", "cosim-cst:latest")
    f1.config("command", f"python3 simple_federate.py {f1.name} {federation.scenario_name}")

    if with_docker:
        f2.config("image", "cosim-cst:latest")
    f2.config("command", f"python3 simple_federate.py {f2.name} {federation.scenario_name}")

    federation.write_config("2023-12-07T15:31:27", "2023-12-08T15:31:27")

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