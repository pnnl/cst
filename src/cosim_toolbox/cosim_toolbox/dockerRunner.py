import os
import pprint
import logging
import subprocess
import cosim_toolbox as cst
from cosim_toolbox.dbConfigs import DBConfigs

logger = logging.getLogger(__name__)
pp = pprint.PrettyPrinter(indent=4, )

class DockerRunner:
    """Collection of static methods used in building and running the docker-compose.yaml
    for running a new service or simulator.
    """
    @staticmethod
    def _service(name: str, image: str, env: list, cnt: int, depends: str = None) -> str:
        """Builds the "service" part of the docker-compose.yaml

        Args:
            name (str): Name of the service being defined
            image (str): Name of the image on which the service runs
            env (list): Environment in image the service utilizes
            cnt (int): Index used to define the IP for the service in the Docker virtual network
            depends (str, optional): Dependency for service being defined. Defaults to None.

        Returns:
            str: _description_
        """
        _service = "  " + name + ":\n"
        _service += "    image: \"" + image + "\"\n"
        if env[0] != '':
            _service += "    environment:\n"
            _service += env[0]
        _service += "    user: worker\n"
        _service += "    working_dir: /home/worker/case\n"
        _service += "    volumes:\n"
        _service += "      - .:/home/worker/case\n"
        _service += "      - ../../../data:/home/worker/tesp/data\n"
        if depends is not None:
            _service += "    depends_on:\n"
            _service += "      - " + depends + "\n"
        _service += "    networks:\n"
        _service += "      cu_net:\n"
        _service += "        ipv4_address: 10.5.0." + str(cnt) + "\n"
        _service += "    command: /bin/bash -c \"" + env[1] + "\"\n"
        return _service

    @staticmethod
    def _network() -> str:
        """Creates a template of the Docker network for use in creating the docker-compose.yaml

        Returns:
            str: Docker network template as a string
        """
        _network = 'networks:\n'
        _network += '  cu_net:\n'
        _network += '    driver: bridge\n'
        _network += '    ipam:\n'
        _network += '      config:\n'
        _network += '        - subnet: 10.5.0.0/16\n'
        _network += '          gateway: 10.5.0.1\n'
        return _network

    @staticmethod
    def define_yaml(scenario_name: str) -> None:
        """Create the docker-compoose.yaml for the provided scenario

        Args:
            scenario_name (str): Name of the scenario run by this docker-compose.yaml
        """
        mdb = DBConfigs(cst.cosim_mongo, cst.cosim_mongo_db)

        scenario_def = mdb.get_dict(cst.cu_scenarios, None, scenario_name)
        federation_name = scenario_def["federation"]
        schema_name = scenario_def["schema"]
        fed_def = mdb.get_dict(cst.cu_federations, None, federation_name)["federation"]

        cosim_env = """      SIM_HOST: \"""" + cst.sim_host + """\"
      SIM_USER: \"""" + cst.sim_user + """\"
      POSTGRES_HOST: \"""" + cst.cosim_pg_host + """\"
      MONGO_HOST: \"""" + cst.cosim_mg_host + """\"
      MONGO_PORT: \"""" + cst.cosim_mg_port + """\"
"""
        yaml = 'services:\n'
        # Add helics broker federate
        cnt = 2
        fed_cnt = str(fed_def.__len__() + 1)
        env = [cosim_env, "exec helics_broker --ipv4 -f " + fed_cnt + " --loglevel=warning --name=broker"]
        yaml += DockerRunner._service("helics", "cosim-helics:latest", env, cnt, depends=None)

        for name in fed_def:
            cnt += 1
            image = fed_def[name]['image']
            env = [cosim_env, fed_def[name]['command']]
            yaml += DockerRunner._service(name, image, env, cnt, depends=None)

        # Add data logger federate
        cnt += 1
        env = [cosim_env,
               "source /home/worker/venv/bin/activate && " +
               "exec python3 -c \\\"import cosim_toolbox.federateLogger as datalog; datalog.main('FederateLogger', '" +
               schema_name + "', '" + scenario_name + "')\\\""]
        yaml += DockerRunner._service(cst.cu_logger, "cosim-python:latest", env, cnt, depends=None)

        yaml += DockerRunner._network()
        op = open(scenario_name + ".yaml", 'w')
        op.write(yaml)
        op.close()

    @staticmethod
    def run_yaml(scenario_name: str) -> None:
        """Runs the provided scenario by calling the appropriate docker-compose.yaml

        Args:
            scenario_name (str): Name of the scenario run by this docker-compose.yaml
        """
        logger.info('====  ' + scenario_name + ' Broker Start in\n        ' + os.getcwd())
        docker_compose = "docker compose -f " + scenario_name + ".yaml"
        subprocess.Popen(docker_compose + " up", shell=True).wait()
        subprocess.Popen(docker_compose + " down", shell=True).wait()
        logger.info('====  Broker Exit in\n        ' + os.getcwd())

    @staticmethod
    def run_remote_yaml(scenario_name: str, path: str = "/run/python/test_federation") -> None:
        """Runs the docker-compose.yaml on a remote compute node

        Args:
            scenario_name (str): Name of the scenario run by this docker-compose.yaml
            path (str, optional): Path to docker-compose-yaml on remote hose. Defaults to "/run/python/test_federation".
        """
        cosim = os.environ.get("SIM_DIR", "/home/worker/copper")
        logger.info('====  ' + scenario_name + ' Broker Start in\n        ' + os.getcwd())
        docker_compose = "docker compose -f " + scenario_name + ".yaml"
        # in wsl_post and wsl_host
        if not cst.wsl_host:
            ssh = "ssh -i ~/copper-key-ecdsa " + cst.sim_user + "@" + cst.sim_host
        else:
            ssh = "ssh -i ~/copper-key-ecdsa " + cst.sim_user + "@" + cst.wsl_host
        cmd = ("sh -c 'cd " + cosim + path + " && " + docker_compose + " up && " + docker_compose + " down'")
        subprocess.Popen(ssh + " \"nohup " + cmd + " > /dev/null &\"", shell=True)
        logger.info('====  Broker Exit in\n        ' + os.getcwd())
