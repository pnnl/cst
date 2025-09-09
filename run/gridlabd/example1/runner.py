"""

"""
from cosim_toolbox.dockerRunner import DockerRunner
from cosim_toolbox.dbConfigs import DBConfigs
from configurator import Configurator

if __name__ == "__main__":
    remote = False
    with_docker = True
    _scenario_name = "gld2"
    _analysis_name = "gld2"
    _federation_name = "gld2"
    configurator = Configurator(_scenario_name, _analysis_name, _federation_name, docker=with_docker)
    broker_address = None
    if with_docker:
        broker_address = "10.5.0.2"
    configurator.add_python_federate_from_config("controller_config.json", "controller.py", broker_address=broker_address)
    configurator.add_gridlabd_federate_from_config("gld_config.json", "tiny_main.glm", broker_address=broker_address)
    # configurator.store_federation_config(_federation_name)
    mdb = DBConfigs()
    mdb.store_scenario(
        scenario_name=_scenario_name,
        analysis_name=_analysis_name,
        federation_name = _federation_name,
        start = "2023-12-07T15:31:27",
        stop = "2023-12-07T18:31:27",
        docker = with_docker
        )
    mdb.store_federation_config(_federation_name, configurator.federation_config)
    print(configurator.federation_config)
    if with_docker:
        DockerRunner.define_yaml(_scenario_name)
        if remote:
            DockerRunner.run_remote_yaml(_scenario_name)
        else:
            DockerRunner.run_yaml(_scenario_name)
    # else:
    #     run(_scenario_name)
