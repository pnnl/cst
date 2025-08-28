import os
import logging
import subprocess

import cosim_toolbox as env
from cosim_toolbox.dbConfigs import DBConfigs

logger = logging.getLogger(__name__)

class DockerRunner:
    """Collection of static methods used in building and running the docker-compose.yaml
    for running a new service or simulator.
    """
    @staticmethod
    def _service(name: str, image: str, params: list, cnt: int, depends: str = None) -> str:
        """Builds the "service" part of the docker-compose.yaml

        Args:
            name (str): Name of the service being defined
            image (str): Name of the image on which the service runs
            params (list): Environment in image the service utilizes
            cnt (int): Index used to define the IP for the service in the Docker virtual network
            depends (str, optional): Dependency for service being defined. Defaults to None.

        Returns:
            str: _description_
        """
        _service = "  " + name + ":\n"
        _service += "    image: \"" + image + "\"\n"
        if params[0] != '':
            _service += "    environment:\n"
            _service += params[0]
        _service += "    user: worker\n"
        _service += "    working_dir: /home/worker/case\n"
        _service += "    volumes:\n"
        _service += "      - .:/home/worker/case\n"
        _service += "      - ../../../data:/home/worker/tesp/data\n"
        if depends is not None:
            _service += "    depends_on:\n"
            _service += "      - " + depends + "\n"
        _service += "    networks:\n"
        _service += "      cst_net:\n"
        _service += "        ipv4_address: 10.5.0." + str(cnt) + "\n"
        _service += "    command: /bin/bash -c \"" + params[1] + "\"\n"
        return _service

    @staticmethod
    def _network() -> str:
        """Creates a template of the Docker network for use in creating the docker-compose.yaml

        Returns:
            str: Docker network template as a string
        """
        _network = 'networks:\n'
        _network += '  cst_net:\n'
        _network += '    driver: bridge\n'
        _network += '    ipam:\n'
        _network += '      config:\n'
        _network += '        - subnet: 10.5.0.0/16\n'
        _network += '          gateway: 10.5.0.1\n'
        return _network

    @staticmethod
    def define_yaml(scenario_name: str) -> None:
        """Create the docker-compose.yaml for the provided scenario

        Args:
            scenario_name (str): Name of the scenario
        """
        db = DBConfigs(env.cst_mongo, env.cst_mongo_db)

        scenario_def = db.get_dict(env.cst_scenarios, None, scenario_name)
        federation_name = scenario_def["federation"]
        schema_name = scenario_def["schema"]
        fed_def = db.get_dict(env.cst_federations, None, federation_name)["federation"]

        cosim_env = """      CST_HOST: \"""" + env.cst_host + """\"
      LOCAL_USER: \"""" + env.local_user + """\"
      POSTGRES_HOST: \"""" + env.cst_pg_host + """\"
      MONGO_HOST: \"""" + env.cst_mg_host + """\"
      MONGO_PORT: \"""" + env.cst_mg_port + """\"
"""
        # Add helics broker federate
        cnt = 2
        yaml = ""
        add_logger = False
        for name in fed_def:
            cnt += 1
            image = fed_def[name]['image']
            commandline = f"{fed_def[name]['command']}"
            if 'prefix' in fed_def[name]:
                if fed_def[name]['prefix'] != "":
                    commandline = f"{fed_def[name]['prefix']} && " + commandline
            params = [cosim_env, commandline]
            yaml += DockerRunner._service(name, image, params, cnt, depends=None)
            if 'logger' in fed_def[name]:
                if fed_def[name]['logger']:
                    add_logger = True

        # Add data logger federate
        if add_logger:
            cnt += 1
            params = [cosim_env,
                   f"python3 -c \"import cosim_toolbox.federateLogger as datalog; "
                   f"datalog.main('FederateLogger', '{schema_name}', '{scenario_name}')\""]
            yaml += DockerRunner._service("cst_logger", "cosim-cst:latest", params, cnt, depends=None)

        yaml += DockerRunner._network()

        # fed_cnt = str(fed_def.__len__())
        params = [cosim_env, f"helics_broker --ipv4 -f {cnt-2} --loglevel=warning --name=broker"]
        yaml = 'services:\n' + DockerRunner._service("helics", "cosim-cst:latest", params, 2, depends=None) + yaml

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
            TODO: Test, 'path' have not been set in examples at this point

        Args:
            scenario_name (str): Name of the scenario run by this docker-compose.yaml
            path (str, optional): Path to docker-compose-yaml on remote hose. Defaults to "/run/python/test_federation".
        """
        cosim = os.environ.get("CST_ROOT", "/home/worker/copper")
        logger.info('====  ' + scenario_name + ' Broker Start in\n        ' + os.getcwd())
        docker_compose = "docker compose -f " + scenario_name + ".yaml"
        # in wsl_post and wsl_host
        if not env.wsl_host:
            ssh = "ssh -i ~/copper-key-ecdsa " + env.local_user + "@" + env.cst_host
        else:
            ssh = "ssh -i ~/copper-key-ecdsa " + env.local_user + "@" + env.wsl_host
        cmd = ("sh -c 'cd " + cosim + path + " && " + docker_compose + " up && " + docker_compose + " down'")
        subprocess.Popen(ssh + " \"nohup " + cmd + " > /dev/null &\"", shell=True)
        logger.info('====  Broker Exit in\n        ' + os.getcwd())

    @staticmethod
    def define_sh(scenario_name: str) -> None:
        """Create the run shell file for the provided scenario

        Args:
            scenario_name (str): Name of the scenario
        """
        db = DBConfigs(env.cst_mongo, env.cst_mongo_db)

        scenario_def = db.get_dict(env.cst_scenarios, None, scenario_name)
        federation_name = scenario_def["federation"]
        schema_name = scenario_def["schema"]
        fed_def = db.get_dict(env.cst_federations, None, federation_name)["federation"]

        cnt = 2
        shell = ""
        add_logger = False
        for name in fed_def:
            cnt += 1
            commandline = f"(exec {fed_def[name]['command']} &> {name}.log &)\n"
            if 'prefix' in fed_def[name]:
                if fed_def[name]['prefix'] != "":
                    commandline = f"{fed_def[name]['prefix']} && " + commandline
            shell += commandline
            if 'logger' in fed_def[name]:
                if fed_def[name]['logger']:
                    add_logger = True

        # Add data logger federate
        if add_logger:
            cnt += 1
            shell += f"(exec python3 -c \"import cosim_toolbox.federateLogger as datalog; " \
                     f"datalog.main('FederateLogger', '{schema_name} ', '{scenario_name}')\" &> FederateLogger.log &)"

        # Add helics broker federate
        shell = f"#!/bin/bash\n\n" \
                f"(exec helics_broker -f {cnt-2} --loglevel=warning --name=broker &> broker.log &)\n" + shell

        op = open(f"{scenario_name}.sh", 'w')
        op.write(shell)
        op.close()
        subprocess.run(['chmod', '+x', f"{scenario_name}.sh"])
