"""
Created on 30 June 2025

Defines the Federation class which is used to programmatically
define a federation of federate class modules the pubs and subs of those federates
using helicsMsg class and write it out to a federation configuration JSON.

@author:
mitch.pelton@pnnl.gov
"""

from .helicsConfig import HelicsPubGroup, HelicsSubGroup, HelicsMsg
from cosim_toolbox.dbms import create_metadata_manager


class FederateConfig:
    # logger for federate logger
    # image for docker
    # prefix for export and other commands for docker and sh
    # command for docker and sh
    # federate_type -> value | combo | message,
    _config_var = {
        "name": "",
        "logger": True,
        "image": "None",
        "prefix": "",
        "command": "None",
        "federate_type": "combo",
        "HELICS_config": {}
    }

    def __init__(self, name: str, **kwargs):
        self._unique_id = 0
        self.name = name
        self.outputs = {}
        self.inputs = {}
        self.endpoints = {}
        self._fed_cnfg = {}
        self.config("logger", False)
        self.config("image", "")
        self.config("command", "")
        self.config("federate_type", "value")

        kwargs.setdefault("terminate_on_error", True)
        helics = HelicsMsg(name, **kwargs)
        self.helics:HelicsMsg = helics

    def unique(self) -> str:
        guid = f"id_{self._unique_id}"
        self._unique_id += 1
        return guid

    def config(self, _n: str, _v: any) -> dict:
        """
        Adds key specified by first parameter with value specified
        by the second parameter to the federate config ("_fed_cnfg")
        attribute of this object

        Args:
            _n (str): Key under which new attribute will be added
            _v (any): Value added to dictionary

        Returns:
            dict: Dictionary to which the new value was added.
        """
        if HelicsMsg.verify(self._config_var, _n, _v):
            self._fed_cnfg[_n] = _v
        return self._fed_cnfg

    def find_output_group(self, key: str) -> None | tuple:
        for name, group in self.outputs.items():
            for var in group.vars:
                if var["key"] == key:
                    return self.name, group.name
        return None

    def find_input_group(self, key: str) -> None | tuple:
        for name, group in self.inputs.items():
            for var in group.vars:
                if var["key"] == key:
                    return group.fed, group.name
        return None

    def docker(self, address: int=0):
        if address > 0:
            self.helics.config("broker_address", f"10.5.0.{address}")

    def define_io(self):
        for name, group in self.outputs.items():
            for i in group.vars:
                self.helics.publication(i)
        for name, group in self.inputs.items():
            for i in group.vars:
                self.helics.subscription(i)
        for name, group in self.endpoints.items():
            for i in group.vars:
                self.helics.end_point(i)
        # uncomment for debugging
        # self.helics.write_file(self.name + ".json")


class FederationConfig:

    def __init__(self, scenario_name: str, analysis_name: str, federation_name: str,
                 docker: bool=False, use_meta_db: str = "mongo", use_data_db: str = "postgres"):

        # use_meta_db for meta database -> mongo | json
        # use_data_db for timeseries database -> postgres | csv

        self.scenario_name = scenario_name
        self.analysis_name = analysis_name   # analysis
        self.federation_name = federation_name
        self.docker = docker
        self.use_meta_db = use_meta_db
        self.use_data_db = use_data_db
        self.address = 2
        self.federates = {}

    def del_federate_config(self, name: str):
        del self.federates[name]

    def add_federate_config(self, fed: FederateConfig):
        if isinstance(fed, FederateConfig):
            self.federates[fed.name] = fed
            if self.docker:
                self.address += 1
                fed.docker(self.address)
        return fed

    def add_group(self, name: str, data_type: str, key_format: dict, **kwargs):
        if "src" in key_format:
            src_format = key_format["src"]
            from_config = self.federates[src_format["from_fed"]]
            src_type = data_type
            if "datatype" in src_format:
                src_type = src_format["datatype"]
            pub_group = HelicsPubGroup(name, src_type, src_format, **kwargs)
            from_config.outputs[from_config.unique()] = pub_group
            if "des" in key_format:
                for des_format in key_format["des"]:
                    to_config = self.federates[des_format["to_fed"]]
                    des_type = data_type
                    if "datatype" in des_format:
                        des_type = des_format["datatype"]
                    if "globl" in kwargs:
                        kwargs.pop("globl")
                    if "tags" in kwargs:
                        kwargs.pop("tags")
                    sub_group = HelicsSubGroup(name, des_type, des_format, **kwargs)
                    to_config.inputs[to_config.unique()] = sub_group
                    if "keys" not in des_format:
                        self.add_group_subs(pub_group, sub_group, des_format)

    def define_io(self):
        for name, fed in self.federates.items():
            fed.define_io()

    def check_pubs(self) -> dict:
        missing = {}
        for pub_name, pub_fed in self.federates.items():
            not_found = []
            miss_match = []
            missing[pub_name] = {}
            pubs = pub_fed.helics.get_pubs()
            for pub in pubs:
                found = False
                fed, grp = pub_fed.find_output_group(pub["key"])
                for sub_name, sub_fed in self.federates.items():
                    if pub_name == sub_name:
                        continue
                    subs = sub_fed.helics.get_subs()
                    for sub in subs:
                        if pub["key"] in sub["key"]:
                            found = True
                            s_fed, s_grp = sub_fed.find_input_group(sub["key"])
                            if sub_name != pub_name and grp != s_grp:
                                miss_match.append(f"{pub_name}, {fed}, {grp}:{sub_name}, {s_fed}, {s_grp}")
                            break
                if not found:
                    not_found.append(pub["key"])
            missing[pub_name]["NotFound"] = not_found
            missing[pub_name]["Missmatch"] = miss_match
        return missing

    def check_subs(self) -> dict:
        missing = {}
        for sub_name, sub_fed in self.federates.items():
            not_found = []
            miss_match = []
            missing[sub_name] = {}
            subs = sub_fed.helics.get_subs()
            for sub in subs:
                found = False
                fed, grp = sub_fed.find_input_group(sub["key"])
                for pub_name, pub_fed in self.federates.items():
                    if sub_name == pub_name:
                        continue
                    pubs = pub_fed.helics.get_pubs()
                    for pub in pubs:
                        if pub["key"] in sub["key"]:
                            found = True
                            p_fed, p_grp = pub_fed.find_output_group(pub["key"])
                            if sub_name != pub_name and grp != p_grp:
                                miss_match.append(f"{pub_name}, {fed}, {grp}:{sub_name}, {p_fed}, {p_grp}")
                            break
                if not found:
                    not_found.append(sub["key"])
            missing[sub_name]["NotFound"] = not_found
            missing[sub_name]["Missmatch"] = miss_match
        return missing

    @staticmethod
    def add_group_subs(pub_group:HelicsPubGroup, sub_group:HelicsSubGroup, des_format:dict):
        pubs = pub_group.vars
        for pub in pubs:
            parts = pub["key"].split("/")
            property_name = parts[-1]
            sub = sub_group.diction.copy()
            sub["key"] = des_format["from_fed"] + "/" + pub["key"]
            if "info" in des_format:
                obj = parts[len(parts) - 2]
                sub["info"] = { "object": obj, "property": property_name }
            sub_group.vars.append(sub)

    def add_subs(self, from_fed: str, to_fed_list: list, info: bool = False):
        fed_from: FederateConfig = self.federates[from_fed]
        for to_fed in to_fed_list:
            fed_to = self.federates[to_fed]
            for pub_name, pub_group in fed_to.outputs.items():
                pubs = pub_group.vars
                for pub in pubs:
                    parts = pub["key"].split("/")
                    property_name = parts[-1]
                    for name, group in fed_from.inputs.items():
                        if group.name in property_name:
                            sub = group.diction.copy()
                            sub["key"] = to_fed + "/" + pub["key"]
                            if info:
                                obj = parts[len(parts) - 2]
                                sub["info"] = { "object": obj, "property": property_name }
                            group.vars.append(sub)
                            break

    def add_pub_sub(self, from_fed: HelicsMsg, to_fed: HelicsMsg,
                    v_name: str, v_type: str, v_unit: str):
        from_fed.pubs_e(from_fed.name + "/" + v_name, v_type, v_unit)
        to_fed.subs_e(from_fed.name + "/" + v_name, v_type, v_unit)

    def write_file_helics_configs(self):
        """
        This method iterates through all registered federates, generates their
        individual HELICS JSON configurations, and write them on disk.

        """
        for name, fed in self.federates.items():
            # This generates the HELICS config and adds it to the federate's internal config
            fed.helics.write_file(f"{name}.json")

    def get_federation_document(self) -> dict:
        """
        Builds and returns the complete federation configuration document.

        This method iterates through all registered federates, generates their
        individual HELICS JSON configurations, and compiles them into a single
        dictionary that defines the entire federation.

        Returns:
            dict: The federation configuration document, ready to be
                  serialized (e.g., to a JSON file or database).
        """
        document = {"federation": {}}
        for name, fed in self.federates.items():
            # This generates the HELICS config and adds it to the federate's internal config
            fed.config("HELICS_config", fed.helics.write_json())
            # The fed._fed_cnfg now contains the complete federate definition
            document["federation"][name] = fed._fed_cnfg
        return document

    def get_scenario_document(self, start_time: str, stop_time: str) -> dict:
        """
        Builds and returns the scenario configuration document.

        Args:
            start_time (str): The simulation start time (e.g., "2023-12-07T15:31:27").
            stop_time (str): The simulation stop time (e.g., "2023-12-08T15:31:27").

        Returns:
            dict: The scenario configuration document, ready to be
                  serialized.
        """
        return {
            "analysis": self.analysis_name,
            "federation": self.federation_name,
            "start_time": start_time,
            "stop_time": stop_time,
            "docker": self.docker,
        }

    def write_config(self, start, stop):
        # Use the new database management system (dbms) API to write the configurations to disk.
        # Here, we use a JSON backend, but this could easily be switched to 'mongo'.
        with create_metadata_manager(self.use_meta_db) as mgr:
            federation_doc = self.get_federation_document()
            scenario_doc = self.get_scenario_document(start_time=start, stop_time=stop)
            print(f"Writing configuration files to '{mgr.location}'...")
            mgr.write_federation(self.federation_name, federation_doc, overwrite=True)
            mgr.write_scenario(self.scenario_name, scenario_doc, overwrite=True)
            print("Configuration files written successfully.")


def _mytest():
    remote = False
    with_docker = False
    federation = FederationConfig("MyTestScenario", "MyTestAnalysis", "MyTestFederation", with_docker)
    f1 = federation.add_federate_config(FederateConfig("Battery", period=30))
    f2 = federation.add_federate_config(FederateConfig("EVehicle", period=30))

    federation.add_pub_sub(f1.helics, f2.helics, "EV1_current", "double", "A")
    f1.config("image", "cosim-cst:latest")
    f1.config("command", f"python3 simple_federate.py {f1.name} {federation.scenario_name}")

    federation.add_pub_sub(f2.helics, f1.helics, "EV1_voltage", "double", "V")
    f2.config("image", "cosim-cst:latest")
    f2.config("command", f"python3 simple_federate.py {f2.name} {federation.scenario_name}")
    federation.define_io()

    federation.write_config("2023-12-07T15:31:27", "2023-12-08T15:31:27")

if __name__ == "__main__":
    _mytest()