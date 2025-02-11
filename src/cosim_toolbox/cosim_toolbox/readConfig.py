import logging

import cosim_toolbox as env
from cosim_toolbox.dbConfigs import DBConfigs

logger = logging.getLogger(__name__)


class ReadConfig:
    def __init__(self, scenario_name: str):
        self.scenario_name = scenario_name
        # open Mongo Database to retrieve scenario data (metadata)
        meta_db = DBConfigs(env.cst_mg_host, env.cst_mongo_db)
        # retrieve data from MongoDB
        self.scenario = meta_db.get_dict(env.cst_scenarios, None, scenario_name)
        self.schema_name = self.scenario.get("schema")
        self.federation_name = self.scenario.get("federation")
        self.start_time = self.scenario.get("start_time")
        self.stop_time = self.scenario.get("stop_time")
        self.use_docker = self.scenario.get("docker")
        if self.federation_name is not None:
            self.federation = meta_db.get_dict(env.cst_federations, None, self.federation_name)
        # meta_db = None
