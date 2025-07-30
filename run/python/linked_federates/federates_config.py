"""
Created on 7/7/2023

@author: Mitch Pelton
mitch.pelton@pnnl.gov
"""

import simple_config
import simple_config2
import cosim_toolbox.federation as fed
from cosim_toolbox.dockerRunner import DockerRunner

def main():
    remote = False
    with_docker = False
    names = ["Battery", "EVehicle"]
    federation = fed.FederationConfig("MyTestScenario", "MyTestSchema", "MyTestFederation", with_docker)

    f1 = federation.add_federate_config(simple_config.MyFederate(names[0], period=30))
    f2 = federation.add_federate_config(simple_config2.MyFederate(names[1], period=60))
    federation.define_io()

    if with_docker:
        f1.config("image", "cosim-cst:latest")
    f1.config("command", f"python3 simple_federate.py {f1.name} {federation.scenario_name}")

    if with_docker:
        f2.config("image", "cosim-cst:latest")
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
    main()