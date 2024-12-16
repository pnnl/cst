"""
Created on 12/14/2023

Data logger class that defines the basic operations of Python-based logger 
federate in Cosim Toolbox. This is instantiated to create a federate that
collects data from the federates sent via HELICS and pushes it into the 
time-series database. All the HELICS functionality is contained in the 
Federate class.

@author:
mitch.pelton@pnnl.gov
"""
import sys
import logging

from cosim_toolbox.federate import Federate
from cosim_toolbox.dbResults import DBResults as DataLogger
from cosim_toolbox.helicsConfig import HelicsMsg

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.ERROR)

class FederateLogger(Federate):

    def __init__(self, fed_name: str = "", scheme_name: str = "default", **kwargs):
        super().__init__(fed_name, **kwargs)
        self.scheme_name = scheme_name
        self.fed_pubs = None
        self.dl = DataLogger()
        self.dl.open_database_connections()
        self.dl.check_version()
        # save possibilities yes, no, maybe
        self.collect = "maybe"
        self.interval = 40
        self._count = 0
        # uncomment debug, clears schema
        # which means all scenarios are gone in that scheme
        # self.dl.drop_schema(self.scheme_name)
        self.dl.create_schema(self.scheme_name)
        self.dl.make_logger_database(self.scheme_name)

    def connect_to_helics_config(self) -> None:
        """Sets a few class attributes related to HELICS configuration.

        Also determines which publications need to be pushed into the 
        time-series database.
        
        Overload of Federate method
        """

        
        self.federate_type = "combo"
        self.time_step = 30.0 # TODO: This shouldn't be hard-coded, right?
        publications = []
        self.fed_pubs = {}

        #  federateLogger yes, no, maybe
        if self.collect == "no":
            for fed in self.federation:
                self.fed_pubs[fed] = []
        elif self.collect == "yes":
            for fed in self.federation:
                self.fed_pubs[fed] = []
                config = self.federation[fed]["HELICS_config"]
                if "publications" in config.keys():
                    for pub in config["publications"]:
                        publications.append(pub)
                        self.fed_pubs[fed].append(pub["key"])
        else:
            for fed in self.federation:
                self.fed_pubs[fed] = []
                config = self.federation[fed]["HELICS_config"]
                fed_collect = "maybe"
                if self.federation[fed].get("tags"):
                    fed_collect = self.federation[fed]["tags"].get("logger", fed_collect)
                logger.info("fed_collect -> " + fed_collect)

                if "publications" in config.keys():
                    for pub in config["publications"]:
                        item_collect = "maybe"
                        if pub.get("tags"):
                            item_collect = pub["tags"].get("logger", item_collect)
                        logger.info(pub["key"] + " collect -> " + item_collect)

                        if fed_collect == "no":
                            if item_collect == "yes":
                                publications.append(pub)
                                self.fed_pubs[fed].append(pub["key"])
                        else:  # fed_collect == "yes" or "maybe"
                            if item_collect == "yes" or item_collect == "maybe":
                                publications.append(pub)
                                self.fed_pubs[fed].append(pub["key"])

        t1 = HelicsMsg(self.federate_name, self.time_step)
        t1.config("core_type", "zmq")
        t1.config("log_level", "warning")
        t1.config("terminate_on_error", True)
        if self.scenario["docker"]:
            t1.config("brokeraddress", "10.5.0.2")
        self.config = t1.config("subscriptions", publications)
        logger.debug(f"Subscribed pubs {publications}")

    def update_internal_model(self) -> None:
        """Takes latest published values or sent messages (endpoints) and
        pushes them back into the time-series database.
        """
        query = ""
        for key in self.data_from_federation["inputs"]:
            qry = ""
            value = self.data_from_federation["inputs"][key]

            for table in DataLogger.hdt_type.keys():
                if self.inputs[key]['type'].lower() in table.lower():
                    if len(self.fed_pubs):
                        for fed in self.fed_pubs:
                            if key in self.fed_pubs[fed]:
                                logger.debug(f"type {self.inputs[key]['type']}")
                                qry = (f"INSERT INTO {self.scheme_name}.{table} "
                                       "(real_time, sim_time, scenario, federate, sim_name, sim_value)"
                                       f" VALUES( to_timestamp('{self.start}','%Y-%m-%dT%H:%M:%S') + interval '1s' * "
                                       f"{self.granted_time}, {self.granted_time}, "
                                       f"'{self.scenario_name}', '{fed}', '{key}', ")
                                if (type(value) is str) or (type(value) is complex) or (type(value) is list):
                                    qry += f" '{value}'); "
                                    logger.debug(f"stype {self.inputs[key]['type']}")
                                else:
                                    qry += f" {value}); "
                                    logger.debug(f"ntype {self.inputs[key]['type']} table {table}")
                                break
                    break
            query += qry
            # add to logger database
        try:
            if query != "":
                with self.dl.data_db.cursor() as cur:
                    self._count += 1
                    cur.execute(query)
                    # simple implementation of to commit once in a while, not every update 
                    if self._count > self.interval:
                        self.dl.data_db.commit()
                        self._count = 0
        except:
            logger.error("Bad data type in update_internal_model")


def main(federate_name: str, scheme_name: str, scenario_name: str) -> None:
    fed_logger = FederateLogger(federate_name, scheme_name)
    fed_logger.dl.remove_scenario(scheme_name, scenario_name)
    fed_logger.dl.data_db.commit()
    fed_logger.create_federate(scenario_name)
    fed_logger.run_cosim_loop()
    fed_logger.destroy_federate()
    fed_logger.dl.close_database_connections(True)


if __name__ == "__main__":
    if sys.argv.__len__() > 3:
        main(sys.argv[1], sys.argv[2], sys.argv[3])
