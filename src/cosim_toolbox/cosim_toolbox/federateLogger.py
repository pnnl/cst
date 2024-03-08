"""
Created on 12/14/2023

Data logger class that defines the basic operations of Python-based logger federate in
Co-Simulation Toolbox.

@author:
mitch.pelton@pnnl.gov
"""
import sys
import logging

from cosim_toolbox.federate import Federate
from cosim_toolbox.dataLogger import DataLogger
from cosim_toolbox.helicsConfig import HelicsMsg

logger = logging.getLogger(__name__)


class FederateLogger(Federate):

    def __init__(self, fed_name: str = "", scheme_name: str = "default", clear: bool = True, **kwargs):
        super().__init__(fed_name, **kwargs)
        self.scheme_name = scheme_name
        self.fed_pubs = None
        self.dl = DataLogger()
        self.dl.open_database_connections()
        self.dl.check_version()
        # uncomment debug, clears schema
        # which means all scenarios are gone in that scheme
        # dl.drop_schema(self.scheme_name)
        self.dl.create_schema(self.scheme_name)
        self.dl.make_logger_database(self.scheme_name)
        if clear:
            self.dl.remove_scenario(self.scheme_name, self.scenario_name)
        self.dl.data_db.commit()

    def connect_to_helics_config(self) -> None:
        self.federate_type = "combo"
        self.time_step = 30.0
        publications = []
        self.fed_pubs = {}

        for fed in self.federation:
            self.fed_pubs[fed] = []
            config = self.federation[fed]["HELICS_config"]
            if "publications" in config.keys():
                for pub in config["publications"]:
                    publications.append(pub)
                    self.fed_pubs[fed].append(pub["key"])

        t1 = HelicsMsg(self.federate_name, self.time_step)
        t1.config("core_type", "zmq")
        t1.config("log_level", "warning")
        t1.config("terminate_on_error", True)
        if self.scenario["docker"]:
            t1.config("brokeraddress", "10.5.0.2")
        self.config = t1.config("subscriptions", publications)

    def update_internal_model(self) -> None:
        query = ""
        for key in self.data_from_federation["inputs"]:
            qry = ""
            value = self.data_from_federation["inputs"][key]

            for table in DataLogger.hdt_type.keys():
                if self.inputs[key]['type'].lower() in table.lower():
                    for fed in self.fed_pubs:
                        if key in self.fed_pubs[fed]:
                            break
                    qry = (f"INSERT INTO {self.scheme_name}.{table} (data_time, scenario, federate, data_name, data_value)"
                           f" VALUES({self.granted_time}, '{self.scenario_name}', '{fed}', '{key}', ")
                    if type(value) is str or type(value) is complex or type(value) is list:
                        qry += f" '{value}'); "
                    else:
                        qry += f" {value}); "
                    break
            query += qry
            # add to logger database
        try:
            if query != "":
                cur = self.dl.data_db.cursor()
                cur.execute(query)
                cur.close()
                self.dl.data_db.commit()
        except:
            logger.error("Bad data type in update_internal_model")


def main(federate_name: str, scheme_name: str, scenario_name: str) -> None:
    fed_logger = FederateLogger(federate_name, scheme_name)
    fed_logger.create_federate(scenario_name)
    fed_logger.run_cosim_loop()
    fed_logger.destroy_federate()
    fed_logger.dl.close_database_connections(True)


if __name__ == "__main__":
    if sys.argv.__len__() > 3:
        main(sys.argv[1], sys.argv[2], sys.argv[3])
