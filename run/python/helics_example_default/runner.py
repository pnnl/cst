"""

"""
import json
from cosim_toolbox.dockerRunner import DockerRunner
from cosim_toolbox.readConfig import ReadConfig
from battery import Battery
from charger import Charger
from multiprocessing import Process
import helics as h
import cosim_toolbox.federateLogger as datalog
import subprocess
from configurator import Configurator


def run(scenario_name):
    subprocess.Popen("pkill -9 -ce helics_broker", shell=True).wait()
    broker = h.helicsCreateBroker("zmq", name=scenario_name, init_string="-f 3")
    print(broker.address)
    print(broker.name)
    print(f"Is broker connected?: {broker.is_connected()}")
    _scenario_name = "HelicsExampleDefault"
    print("Creating processes...")
    batt = Battery(fed_name="Battery")
    charg = Charger(fed_name="Charger")
    p_batt = Process(target=batt.run, args=(_scenario_name,))
    p_charg = Process(target=charg.run, args=(_scenario_name,))
    p_log = Process(target=datalog.main, args=('FederateLogger', _schema_name, _scenario_name))
    print("Starting Processes...")
    # p_broker = Process(target=h.helicsCreateBroker, args=("zmq", "", f"--federates=3"))
    # p_broker.start()
    p_charg.start()
    p_batt.start()
    p_log.start()
    print("Joining Processes...")
    p_batt.join()
    p_charg.join()
    p_log.join()
    print("All processes finished.")
    # p_broker.join()


if __name__ == "__main__":
    remote = False
    with_docker = True
    _scenario_name = "HelicsExampleDefault"
    _schema_name = "HelicsExampleDefaultSchema"
    _federation_name = "HelicsExampleDefaultFederation"
    configurator = Configurator(_scenario_name, _schema_name, _federation_name, docker=with_docker)
    if with_docker:
        broker_address = "10.5.0.2"
    else:
        broker_address = "localhost"
    configurator.add_python_federate_from_config("BatteryConfig.json", "battery.py", broker_address=broker_address)
    configurator.add_python_federate_from_config("ChargerConfig.json", "charger.py", broker_address=broker_address)
    configurator.store_federation_config(_federation_name)
    configurator.store_scenario(
        scenario_name=_scenario_name, 
        schema_name=_schema_name, 
        federation_name = _federation_name, 
        start = "2023-12-07T15:31:27",
        stop = "2023-12-08T15:31:27",
        docker = with_docker
        )
    print(json.dumps(ReadConfig(_scenario_name).federation, indent=2))
    if with_docker:
        DockerRunner.define_yaml(_scenario_name)
        if remote:
            DockerRunner.run_remote_yaml(_scenario_name)
        else:
            DockerRunner.run_yaml(_scenario_name)
    # else:
    #     run(_scenario_name)
