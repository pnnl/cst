import json
import logging
logger = logging.getLogger(__name__)

import cosim_toolbox as env
from cosim_toolbox.dbConfigs import DBConfigs
from cosim_toolbox.dockerRunner import DockerRunner

PYTHON_CMD_PREFIX = "python3 "
GRIDLABD_CMD_PREFIX = "gridlabd "

class Configurator(DBConfigs):

    def __init__(self, 
                 scenario_name: str, 
                 schema_name: str, 
                 federation_name: str, 
                 docker: bool = False, 
                 remote: bool = False):
        self.scenario_name = scenario_name
        self.schema_name = schema_name
        self.federation_name = federation_name
        self.docker = docker
        self.remote = remote
        self.db = DBConfigs(env.cst_mongo, env.cst_mongo_db)
        self.federation_config = {"federation": {}}

    def _get_federate_type(self, config: dict) -> str:
        has_publications = False
        has_subscriptions = False
        has_endpoints = False
        if "publications" in config.keys():
            if len(config["publications"]) > 0:
                has_publications = True
        if "subscriptions" in config.keys():
            if len(config["subscriptions"]) > 0:
                has_subscriptions = True
        if "endpoints" in config.keys():
            if len(config["endpoints"]) > 0:
                has_endpoints = True
        if not (has_publications or has_subscriptions):
            return "message"
        if has_endpoints:
            return "combo"
        return "value"

    def add_python_federate_from_config(self, config_file, script_path, broker_address: str = None): 
        with open(config_file, "r") as f:
            federate_config = json.load(f)
        if broker_address is not None:
            federate_config["broker_address"] = broker_address
        else:
            federate_config["broker_address"] = "localhost"
        name = federate_config["name"]
        federate_type = self._get_federate_type(federate_config)
        self.federation_config["federation"][name] = {
                "image": "cosim-cst:latest",
                "command": PYTHON_CMD_PREFIX + script_path,
                "federate_type": federate_type,
                "HELICS_config": federate_config
        } 

    def add_gridlabd_federate_from_config(self, config_file, model_path, broker_address: str = None):
        with open(config_file, "r") as f:
            federate_config = json.load(f)
        if broker_address is not None:
            federate_config["broker_address"] = broker_address
        name = federate_config["name"]
        federate_type = self._get_federate_type(federate_config)
        self.federation_config["federation"][name] = {
                "image": "cosim-cst:latest",
                "command": PYTHON_CMD_PREFIX + "gridlabd_federate.py",
                "model_path": model_path,
                "federate_type": federate_type,
                "HELICS_config": federate_config
        }


    def run_dockerized(self):
        if self.docker:
            DockerRunner.define_yaml(self.scenario_name)
            if self.remote:
                return DockerRunner.run_remote_yaml(self.scenario_name)
            return DockerRunner.run_yaml(self.scenario_name)
        
    # TODO: The following methods may be better as MetaDB methods

    def store_scenario(
            self, 
            scenario_name: str = None,
            schema_name: str = None, 
            federation_name: str = None, 
            start: str = "2023-12-07T12:00:00", 
            stop: str = "2023-12-08T12:00:00", 
            docker: bool = False) -> None:
        
        if scenario_name is None:
            scenario_name = self.scenario_name
        if schema_name is None:
            schema_name = self.schema_name
        if federation_name is None:
            federation_name = self.federation_name
        scenario = self.db.scenario(
            schema_name, 
            federation_name, 
            start,
            stop,
            docker)
        
        self.db.remove_document(env.cst_scenarios, None, scenario_name)
        self.db.add_dict(env.cst_scenarios, scenario_name, scenario)

    def store_federation_config(self, name=None) -> None:
        if name is None:
            name = self.federation_name
        self.db.remove_document(env.cst_federations, None, name)
        self.db.add_dict(env.cst_federations, name, self.federation_config)

    def get_scenario(self, name=None) -> dict:
        if name is None:
            name = self.scenario_name
        if name not in self.list_scenarios():
            logger.error(f"{name} not found in {self.list_scenarios()}.")
        return self.db.get_dict(env.cst_scenarios, None, name)
    
    def get_federation_config(self, name=None) -> dict:
        if name is None:
            name = self.federation_name
        if name not in self.list_federations():
            logger.error(f"{name} not found in {self.list_federations()}.")
        return self.db.get_dict(env.cst_federations, None, name)
    
    def list_scenarios(self) -> list:
        return self.db.get_collection_document_names(env.cst_scenarios)
    
    def list_federations(self) -> list:
        return self.db.get_collection_document_names(env.cst_federations)

    
