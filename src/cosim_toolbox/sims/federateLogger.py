#
"""
Created on 12/14/2023

Data logger class that defines the basic operations of Python-based logger
federate in Cosim Toolbox. This is instantiated to create a Federate that
collects data from the federates sent via HELICS and pushes it into the
time-series database. All the HELICS functionality is contained in the
Federate class.

@author:
mitch.pelton@pnnl.gov
"""

import sys
import logging

from .federate import Federate
from .helicsConfig import HelicsMsg

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)


class FederateLogger(Federate):

    def __init__(self, fed_name: str = "logger", **kwargs):
        super().__init__(fed_name, **kwargs)
        self.fed_pubs = None
        self.fed_pts = None

        # save possibilities yes, no, maybe
        self.collect = "maybe"

        # uncomment debug, clears analysis
        # which means all scenarios are gone in that analysis
        # self.dl.drop_analysis(self.analysis_name)

    def get_helics_config(self) -> None:
        """
        Sets a few class attributes related to HELICS configuration.

        Also determines which publications need to be pushed into the
        time-series database.

        Overload of Federate method
        """
        self.federate_type = "combo"
        publications = []
        self.fed_pubs = {}
        self.fed_pts = {}
        source_targets = []

        # federateLogger yes, no, maybe
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

        t1 = HelicsMsg(self.federate_name, period=30)
        t1.config("log_level", "warning")
        t1.config("terminate_on_error", True)
        if self.scenario["docker"]:
            t1.config("broker_address", "10.5.0.2")
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
        self.no_t_start = self.start.replace("T", " ")

    def update_internal_model(self) -> None:
        """Takes latest published values or sent messages (endpoints) and
        pushes them back into the time-series database using the base class methods.
        """

        # Process Inputs (Publications from other federates)
        for key in self.data_from_federation["inputs"]:
            value = self.data_from_federation["inputs"][key]

            # Find which federate this publication belongs to
            federate_name = None
            if len(self.fed_pubs):
                for fed in self.fed_pubs:
                    if key in self.fed_pubs[fed]:
                        federate_name = fed
                        break

            if federate_name and value is not None:
                input_type = self.inputs[key]["type"].lower()
                table = f"hdt_{input_type}"
                self.write_to_logger(federate_name, key, value, table=table)
                logger.debug(
                    f"Logged input - federate: {federate_name}, key: {key}, value: {value}"
                )

        # Process Endpoints
        for key in self.data_from_federation["endpoints"]:
            for msg in self.data_from_federation["endpoints"][key]:
                self.write_to_logger(
                    msg.original_source,
                    msg.original_destination,
                    msg.data,
                    table="hdt_endpoint",
                    message_time=msg.time,
                )
                logger.debug(
                    f"Logged endpoint - source: {msg.original_source}, dest: {msg.original_destination}, data: {msg.data}"
                )


def main(federate_name: str, scenario_name: str, use_meta_db: str ="mongo", use_data_db: str ="postgres") -> None:
    fed_logger = FederateLogger(federate_name)
    fed_logger.run(scenario_name, use_meta_db, use_data_db)
    del fed_logger


if __name__ == "__main__":
    if len(sys.argv) > 4:
        f_name = sys.argv[1]
        s_name = sys.argv[2]
        meta_db = sys.argv[3]
        data_db = sys.argv[4]
        main(f_name, s_name, meta_db, data_db)
    else:
        # Added a simple usage message for clarity.
        print("Usage: python FederateLogger.py <federate_name> <scenario_name> <meta_db> <data_db>")
