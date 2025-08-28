"""
Created on 30 June 2025

Defines the Federation class which is used to programmatically
define a federation of federate class modules the pubs and subs of those federates
using helicsMsg class and write it out to a federation configuration JSON.

@author:
mitch.pelton@pnnl.gov
"""

import cosim_toolbox as env
from cosim_toolbox.dbConfigs import DBConfigs
from cosim_toolbox.helicsConfig import HelicsPubGroup
from cosim_toolbox.helicsConfig import HelicsSubGroup
from cosim_toolbox.helicsConfig import HelicsMsg


class FederateConfig:
    # logger for federate logger
    # image for docker
    # prefix for export and other commands for docker and sh
    # command for docker and sh
    # federate_type -> value | combo | message,
    config_var = {
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
        """Adds key specified by first parameter with value specified
        by the second parameter to the federate config ("_fed_cnfg")
        attribute of this object

        Args:
            _n (str): Key under which new attribute will be added
            _v (any): Value added to dictionary

        Returns:
            dict: Dictionary to which the new value was added.
        """
        if HelicsMsg.verify(self.config_var, _n, _v):
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
        self.helics.write_file(self.name + ".json")

class FederationConfig:

    def __init__(self, scenario_name: str, schema_name: str, federation_name: str, docker: bool=False):
        self.scenario_name = scenario_name
        self.schema_name = schema_name   # analysis
        self.federation_name = federation_name
        self.docker = docker
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
            sub["key"] = des_format["to_fed"] + "/" + pub["key"]
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

    def write_config(self, start, stop):
        diction = {"federation": {}}
        for name, fed in self.federates.items():
            diction["federation"][name] = fed.config("HELICS_config", fed.helics.write_json())
        # print(diction)
        db = DBConfigs(env.cst_mongo, env.cst_mongo_db)
        db.remove_document(env.cst_federations, None, self.federation_name)
        db.add_dict(env.cst_federations, self.federation_name, diction)
        # print(env.cst_federations, db.get_collection_document_names(env.cst_federations))

        scenario = db.scenario(self.schema_name, self.federation_name, start, stop, self.docker)
        db.remove_document(env.cst_scenarios, None, self.scenario_name)
        db.add_dict(env.cst_scenarios, self.scenario_name, scenario)
        # print(env.cst_scenarios, db.get_collection_document_names(env.cst_scenarios))
