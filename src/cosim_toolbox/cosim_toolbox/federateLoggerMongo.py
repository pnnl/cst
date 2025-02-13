"""
Created on 12/14/2023

Data logger class that defines the basic operations of Python-based logger federate in
CoSimulation Toolbox.

@author:
mitch.pelton@pnnl.gov
"""
import sys
import logging

import cosim_toolbox as env
from cosim_toolbox.federate import Federate
from cosim_toolbox.dataLoggerMongo import DataLoggerMongo
from cosim_toolbox.helicsConfig import HelicsMsg

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

class FederateLoggerMongo(Federate):

    def __init__(self, fed_name: str = "", scenario_name: str = "default", **kwargs):
        logger_connection = env.cst_meta_db
        super().__init__(fed_name, **kwargs)
        self.logging_feds = None
        self.scenario_name = scenario_name
        self.fed_pubs = None
        self.fed_pts = None
        self.dl = DataLoggerMongo()
        self.dl.open_database_connections(logger_connection)
        # self.dl.check_version() # Not currently implemented
        # save possibilities yes, no, maybe
        self.collect = "maybe"
        self.interval = 10000   # records
        self._count = 0
        self._commit_cnt = 0
        self.no_t_start = None

        # uncomment debug, clears schema
        # which means all scenarios are gone in that scheme
        # self.dl.drop_schema(self.scheme_name)

    def create_collections(self) -> list:
        """Creates time-series collections based on the federates being logged

        When logging data using MongoDB in CST, each federate holds data in
        its own collection. This method creates those collections based on the
        federates in "fed_pubs" and "fed_pts" that are non-zero, indicating
        they need to have their data logged.

        This method assumes those two attributes have been populated.
        """
        fed_p = [x for x in self.fed_pubs.keys() if len(self.fed_pubs[x]) > 0]
        fed_e = [x for x in self.fed_pts.keys() if len(self.fed_pts[x]) > 0]
        self.logging_feds = [fed_p, fed_e]

        # Remove redundant elements in the logging_fed list
        # We only need one collection per federate
        logging_feds = list(set(self.logging_feds))

        for fed in logging_feds:
            self.dl.meta_db.create_collection(
                fed, 
                timeseries={
                    'timeField': 'timestamp',
                    'metafield': 'metadata'})
        return self.logging_feds

    def connect_to_helics_config(self) -> None:
        self.federate_type = "combo"
        self.period = 30.0
        publications = []
        self.fed_pubs = {}
        self.fed_pts = {}
        source_targets = []

        #  federateLogger yes, no, maybe
        if self.collect == "no":
            for fed in self.federation:
                self.fed_pubs[fed] = []
                self.fed_pts[fed] = []
        elif self.collect == "yes":
            for fed in self.federation:
                self.fed_pubs[fed] = []
                self.fed_pts[fed] = []
                config = self.federation[fed]["HELICS_config"]
                if "publications" in config.keys():
                    for pub in config["publications"]:
                        publications.append(pub)
                        self.fed_pubs[fed].append(pub["key"])
                if "endpoints" in config.keys():
                    for pts in config["endpoints"]:
                        source_targets.append(pts["key"])
                        self.fed_pts[fed].append(pts["key"])
        else:
            for fed in self.federation:
                self.fed_pubs[fed] = []
                self.fed_pts[fed] = []
                config = self.federation[fed]["HELICS_config"]
                fed_collect = "maybe"
                if self.federation[fed].get("tags"):
                    fed_collect = self.federation[fed]["tags"].get("logger", fed_collect)
                logger.debug("fed_collect -> " + fed_collect)

                if "publications" in config.keys():
                    for pub in config["publications"]:
                        item_collect = "maybe"
                        if pub.get("tags"):
                            item_collect = pub["tags"].get("logger", item_collect)
                        logger.debug(pub["key"] + " collect -> " + item_collect)

                        if fed_collect == "no":
                            if item_collect == "yes":
                                publications.append(pub)
                                self.fed_pubs[fed].append(pub["key"])
                        else:  # fed_collect == "yes" or "maybe"
                            if item_collect == "yes" or item_collect == "maybe":
                                publications.append(pub)
                                self.fed_pubs[fed].append(pub["key"])
                if "endpoints" in config.keys():
                    for pts in config["endpoints"]:
                        item_collect = "maybe"
                        if pts.get("tags"):
                            item_collect = pts["tags"].get("logger", item_collect)
                        logger.debug(pts["name"] + " collect -> " + item_collect)

                        if fed_collect == "no":
                            if item_collect == "yes":
                                source_targets.append(pts["name"])
                                self.fed_pts[fed].append(pts["name"])
                        else:  # fed_collect == "yes" or "maybe"
                            if item_collect == "yes" or item_collect == "maybe":
                                source_targets.append(pts["name"])
                                self.fed_pts[fed].append(pts["name"])

        t1 = HelicsMsg(self.federate_name, self.period)
        t1.config("core_type", "zmq")
        t1.config("log_level", "warning")
        t1.config("terminate_on_error", True)
        if self.scenario["docker"]:
            t1.config("brokeraddress", "10.5.0.2")
        self.config = t1.config("subscriptions", publications)

        endpoints = [{
                "name": self.federate_name + "/logger_endpoint",
                "global": True
            }]
        filters = [{
                "name": "logger_filter",
                "cloning": True,
                "operation": "clone",
                "source_targets": source_targets,
                "delivery": self.federate_name + "/logger_endpoint"
            }]
        self.config = t1.config("endpoints", endpoints)
        self.config = t1.config("filters", filters)
        logger.debug(f"Subscribed pubs {publications}")
        self.no_t_start = self.start.replace('T',' ')

        self.create_collections()

    def update_internal_model(self) -> None:
        """Read in subscriptions and write to database
        """
        # Data that is going to be added to MongoDB is appended to the
        # "query" list
        query = []
        # Inputs
        for key in self.data_from_federation["inputs"]:
            value = self.data_from_federation["inputs"][key]
            # Non-logging publications have empty contents in "fed_pubs"
            if len(self.fed_pubs): 
                for fed in self.fed_pubs:
                    if key in self.fed_pubs[fed]:
                        logged_data = {
                            'timestamp': '',
                            'metadata': {
                                'sim_time': f'{self.granted_time}',
                                'data_name': f'{key}',
                            },
                            'data_value': value
                        }
                        query.append(logged_data)
                        break
            break

        # add to logger database
        try:
            if query != "":
                self._count = len(query)
                # simple implementation of to commit once in a while, not every update
                if self._count > self.interval:
                    self.dl.meta_db.insertMany(query)
                    self._count = 0
                    self._commit_cnt += 1
        except Exception as ex:
            logger.error(f"Bad subscriber\n {ex}")

        # EndPoints
        query = []
        table = "hdt_endpoint"
        for key in self.data_from_federation["endpoints"]:
            for msg in self.data_from_federation["endpoints"][key]:
                logged_data = {
                            'timestamp': '',
                            'metadata': {
                                'sim_time': f'{self.granted_time}',
                                'data_name': f'{key}',
                            },
                            'data_value': value
                        }
                query.append(logged_data)
                logger.debug(f"type: string table: {table}")

        # add to logger database
        try:
            if query != "":
                self._count += len(query)
                # simple implementation of to commit once in a while, not every update
                if self._count > self.interval:
                    self.dl.meta_db.insertMany(query)
                    self._count = 0
                    self._commit_cnt += 1
        except Exception as ex:
            logger.error(f"Bad end point\n {ex}")


def main(federate_name: str, scenario_name: str) -> None:
    fed_logger = FederateLoggerMongo(federate_name, scenario_name)
    # Remove old data for scenario
    fed_logger.dl.remove_scenario(scenario_name)
    fed_logger.create_federate(scenario_name)
    fed_logger.run_cosim_loop()
    fed_logger.dl.close_database_connections()
    logger.info(f"Commit count: {fed_logger._commit_cnt}")
    del fed_logger.dl
    fed_logger.destroy_federate()
    del fed_logger


if __name__ == "__main__":
    if sys.argv.__len__() > 3:
        main(sys.argv[1], sys.argv[2])
