from cosim_toolbox.dbConfigs import DBConfigs
from cosim_toolbox import cosim_mg_host, cosim_mongo_db, cu_scenarios, cu_federations

class ReadConfig:
    def __init__(self, scenario_name: str):
        self.name = scenario_name
        # open Mongo Database to retrieve scenario data (metadata)
        self.meta_db = DBConfigs(uri=cosim_mg_host, db_name=cosim_mongo_db)
        # retrieve data from MongoDB
        self.scenario = self.meta_db.get_dict(cu_scenarios, None, scenario_name)
        self.schema_name = self.scenario.get("schema")
        self.federation_name = self.scenario.get("federation")
        self.start_time = self.scenario.get("start_time")
        self.stop_time = self.scenario.get("stop_time")
        self.use_docker = self.scenario.get("docker")
        if self.federation_name is not None:
            self.federation = self.meta_db.get_dict(cu_federations, None, self.federation_name)
        # close MongoDB client
        if self.meta_db.client is not None:
            self.meta_db.client.close()
        self.meta_db = None