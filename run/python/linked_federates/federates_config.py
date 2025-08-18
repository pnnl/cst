"""
Created on 7/7/2023

@author: Mitch Pelton
mitch.pelton@pnnl.gov
"""

import simple_config
import simple_config2
import cosim_toolbox.federation as fed
from cosim_toolbox.helicsConfig import Collect
from cosim_toolbox.helicsConfig import HelicsEndPtGroup
from cosim_toolbox.federation import FederateConfig
from cosim_toolbox.federation import FederationConfig
from cosim_toolbox.dockerRunner import DockerRunner


def define_federation():
    remote = False
    with_docker = False
    names = ["Battery", "EVehicle"]
    bt = {
        "src": { "from_fed": names[0],
                 "keys": ["", ""],
                 "indices": []},
        "des": [{"from_fed": names[0],
                 "to_fed": names[1],
                 "keys": ["", ""],
                 "indices": []}]
    }
    ev = {
        "src": {"from_fed": names[1],
                "keys": ["", ""],
                "indices": []},
        "des": [{"from_fed": names[1],
                 "to_fed": names[0],
                 "keys": ["", ""],
                 "indices": []}]
    }

    federation = FederationConfig("MyTestScenario", "MyTestSchema", "MyTestFederation", with_docker)
    f1 = federation.add_federate_config(FederateConfig(names[0], period=30))
    f2 = federation.add_federate_config(FederateConfig(names[1], period=60))

    # addGroup from the perspective what is published
    federation.add_group("current", "double", bt, unit="A", globl=True, tags={"logger": Collect.YES.value})
    federation.add_group("current2", "integer", bt, unit="A", globl=True, tags={"logger": Collect.NO.value})
    federation.add_group("current3", "boolean", bt, unit="A")
    federation.add_group("current4", "string", bt, unit="A")
    federation.add_group("current5", "complex", bt, unit="A", globl=True, tags={"logger": Collect.MAYBE.value})
    federation.add_group("current6", "vector", bt, unit="A", globl=True, tags={"logger": Collect.NO.value})

    federation.add_group("voltage", "double", ev, unit="V")
    federation.add_group("voltage2", "integer", ev, unit="V")
    federation.add_group("voltage3", "boolean", ev, unit="V", globl=True, tags={"logger": Collect.NO.value})
    federation.add_group("voltage4", "string", ev, unit="V")
    federation.add_group("voltage5", "complex", ev, unit="V")
    federation.add_group("voltage6", "vector", ev, unit="V")

    f1.endpoints["endpoint1"] = HelicsEndPtGroup("current1", bt["src"], "voltage1", bt["des"][0],
                                                    globl=True, tags={"logger": Collect.YES.value})
    f2.endpoints["endpoint1"] = HelicsEndPtGroup("voltage1", ev["src"], "current1", ev["des"][0],
                                                    tags={"logger": Collect.YES.value})
    f1.helics.collect(Collect.YES)
    f2.helics.collect(Collect.NO)
    federation.define_io()

    f1.config("federate_type", "combo")
    f2.config("federate_type", "combo")
    if with_docker:
        f1.config("image", "cosim-cst:latest")
        f2.config("image", "cosim-cst:latest")
    f1.config("command", f"python3 simple_federate.py {f1.name} {federation.scenario_name}")
    f2.config("command", f"python3 simple_federate2.py {f2.name} {federation.scenario_name}")

    federation.define_scenario("2023-12-07T15:31:27", "2023-12-08T15:31:27")

    if with_docker:
        DockerRunner.define_yaml(federation.scenario_name)
        if remote:
            DockerRunner.run_remote_yaml(federation.scenario_name)
        else:
            DockerRunner.run_yaml(federation.scenario_name)
    else:
        DockerRunner.define_sh(federation.scenario_name)


def define_format():
    remote = False
    with_docker = False
    names = ["Battery", "EVehicle"]
    federation = fed.FederationConfig("MyTestScenario", "MyTestSchema", "MyTestFederation", with_docker)

    f1 = federation.add_federate_config(simple_config.MyFederate(names[0], period=30))
    f2 = federation.add_federate_config(simple_config2.MyFederate(names[1], period=60))
    federation.define_io()

    if with_docker:
        f1.config("image", "cosim-cst:latest")
        f2.config("image", "cosim-cst:latest")
    f1.config("command", f"python3 simple_federate.py {f1.name} {federation.scenario_name}")
    f2.config("command", f"python3 simple_federate2.py {f2.name} {federation.scenario_name}")

    federation.define_scenario("2023-12-07T15:31:27", "2023-12-08T15:31:27")

    if with_docker:
        DockerRunner.define_yaml(federation.scenario_name)
        if remote:
            DockerRunner.run_remote_yaml(federation.scenario_name)
        else:
            DockerRunner.run_yaml(federation.scenario_name)
    else:
        DockerRunner.define_sh(federation.scenario_name)


if __name__ == "__main__":
    # define_format()
    define_federation()
