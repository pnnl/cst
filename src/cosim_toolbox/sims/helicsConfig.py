"""
Created on 20 Dec 2023

Defines the HelicsMsg class which is used to programmatically 
define pubs and subs of a HELICS class and write it out to a
HELICS federation configuration JSON.

@author:
mitch.pelton@pnnl.gov
"""

from enum import Enum
import json


class Group(Enum):
    SUB = 'sub'
    PUB = 'pub'
    INP = 'inp'
    EPT = 'ept'

class Collect(Enum):
    YES = 'yes'
    NO = 'no'
    MAYBE = 'maybe'

class HelicsFormatter:
    def __init__(self, name: str, key_format: dict, group: Group):
        self.seperator = "/"
        self.name = name
        self.fed = key_format["from_fed"]
        if "output_fed" in key_format:
             self.fed = key_format["to_fed"]
        self.format = False
        self.group = group
        self.vars = []
        if "keys" in key_format:
            self.keys = key_format["keys"]
            self.indices = key_format["indices"]
            self.format = True
        self.diction = None

    def format_variables(self):
        variables = []
        if self.format:
            global_fed = ""
            if self.group == Group.SUB:
                global_fed = self.fed + self.seperator
            if "global" in self.diction:
                if self.diction["global"]:
                    global_fed = self.fed + self.seperator
            # Multiples
            if "@@" in self.keys[0] and "##" in self.keys[0]:
                for k in self.indices:
                    for j in range(k[1], k[2]):
                        key:str = self.keys[0]
                        obj:str = self.keys[1]
                        key = key.replace("@@", k[0])
                        obj = obj.replace("@@", k[0])
                        key = key.replace("##", str(j))
                        obj = obj.replace("##", str(j))
                        var = self.diction.copy()
                        var["key"] = global_fed + key + self.seperator + self.name
                        if len(obj) > 0:
                            var["info"] = {"object": obj, "property": self.name}
                        variables.append(var)
            elif "@list@" in self.keys[0]:
                for k in self.indices:
                    key:str = self.keys[0]
                    obj:str = self.keys[1]
                    key = key.replace("@list@", k)
                    obj = obj.replace("@list@", k)
                    var = self.diction.copy()
                    var["key"] = global_fed + key + self.seperator + self.name
                    if len(obj) > 0:
                        var["info"] = {"object": obj, "property": self.name}
                    variables.append(var)
            elif "@@" in self.keys[0]:
                for k in self.indices:
                    key:str = self.keys[0]
                    obj:str = self.keys[1]
                    key = key.replace("@@", k[0])
                    obj = obj.replace("@@", k[0])
                    var = self.diction.copy()
                    if k[1]:
                        var["key"] = global_fed + self.name
                    else:
                        var["key"] = global_fed + key + self.seperator + self.name
                    if len(obj) > 0:
                        if self.group == Group.SUB:
                            var["info"] = {"object": obj, "property": key}
                        else:
                            var["info"] = {"object": obj, "property": self.name}
                    variables.append(var)
            elif "##" in self.keys[0]:
                for k in self.indices:
                    for j in range(k[0], k[1]):
                        key:str = self.keys[0]
                        obj:str = self.keys[1]
                        key = key.replace("##", str(j))
                        obj = obj.replace("##", str(j))
                        var = self.diction.copy()
                        if k[2]:
                            var["key"] = global_fed + self.name
                        else:
                            var["key"] = global_fed + key + self.seperator + self.name
                        if len(obj) > 0:
                            if self.group == Group.SUB:
                                var["info"] = {"object": obj, "property": key}
                            else:
                                var["info"] = {"object": obj, "property": self.name}
                        variables.append(var)
            else:
            # Single
                key = self.keys[0]
                obj = self.keys[1]
                var = self.diction.copy()
                var["key"] = global_fed + key + self.name
                if len(obj) > 0:
                    var["info"] = {"object": obj, "property": self.name}
                variables.append(var)
        self.vars = variables

class HelicsEndpointFormatter:
    def __init__(self, name: str, key_format: dict, destination: str, des_format: dict, group: Group):
        self.seperator = "/"
        self.name = name
        self.destination = destination
        self.fed = key_format["from_fed"]
        self.keys = key_format["keys"]
        self.indices = key_format["indices"]
        self.fed1 = des_format["to_fed"]
        self.keys1 = des_format["keys"]
        self.indices1 = des_format["indices"]
        self.vars = []
        self.diction = None

    def format_endpoints(self):
        variables = []
        global_fed = ""
        if "global" in self.diction:
            if self.diction["global"]:
                global_fed = self.fed + self.seperator
        # Multiples
        if "@@" in self.keys[0] and "##" in self.keys[0]:
            pass
        elif "@@" in self.keys[0]:
            pass
        elif "##" in self.keys[0]:
            pass
        else:
        # Single
            src = self.keys[0]
            s_obj = self.keys[1]
            des = self.keys1[0]
            d_obj = self.keys1[1]
            var = self.diction.copy()
            var["name"] = global_fed + src + self.name
            var["destination"] = self.fed1 + self.seperator + des + self.destination
            if len(s_obj) > 0:
                var["info"] = {"object": s_obj, "property": self.name}
            if len(d_obj) > 0:
                var["info"] = {"object": d_obj, "property": self.destination}
            variables.append(var)
        self.vars = variables

class HelicsPubGroup(HelicsFormatter):
    def __init__(self, name: str, data_type: str, key_format: dict, **kwargs):
        super().__init__(name, key_format, Group.PUB)
        self.diction = {"type": data_type}
        # rename 'globl' to 'global' because of 'global' keyword can not be used in kwargs
        if "globl" in kwargs:
            kwargs["global"] = kwargs["globl"]
            kwargs.pop("globl")
        self.diction.update(kwargs)
        for attr_name, attr in self.diction.items():
            HelicsMsg.verify(HelicsMsg._pub_var, attr_name, attr)
        self.format_variables()

class HelicsSubGroup(HelicsFormatter):
    def __init__(self, name: str, data_type: str, key_format: dict=None, **kwargs):
        super().__init__(name, key_format, Group.SUB)
        self.diction = {"type": data_type}
        self.diction.update(kwargs)
        for attr_name, attr in self.diction.items():
            HelicsMsg.verify(HelicsMsg._sub_var, attr_name, attr)
        self.format_variables()

class HelicsEndPtGroup(HelicsEndpointFormatter):
    def __init__(self, name: str, key_format: dict, destination: str, des_format: dict, **kwargs):
        super().__init__(name, key_format, destination, des_format, Group.EPT)
        self.diction = {}
        # rename 'globl' to 'global' because of 'global' keyword can not be used in kwargs
        if "globl" in kwargs:
            kwargs["global"] = kwargs["globl"]
            kwargs.pop("globl")
        self.diction.update(kwargs)
        for attr_name, attr in self.diction.items():
            HelicsMsg.verify(HelicsMsg._end_pts, attr_name, attr)
        self.format_endpoints()

class HelicsMsg:
    """
    Provides a data structure for building up the HELICS configuration
    definitions for publications and subscriptions.
    """
    _config_var = {
        # General
        "name": "",
        "core_type": "zmq",
        "core_name": "",
        "core_init_string": "",
        "autobroker": False,
        "broker_init_string": "",
        "terminate_on_error": False,
        "source_only": False,
        "observer": False,
        "reentrant":False,
        "broker_key": "",
        # general for pub, subs, inputs
        "only_update_on_change": False,
        "only_transmit_on_change": False,
        "tolerance": 0.0,
        # "default": based on type
        "connection_required": False,
        "connection_optional": True,
        "default_global": False,
        "strict_input_type_checking": False,
        # Logging
        "tags": {},
        "log_file": "",
        "log_level": "none",
        "force_logging_flush": False,
        "file_log_level": "",
        "console_log_level": "",
        "dump_log": False,
        "log_buffer": 10,
        # Timing
        "ignore_time_mismatch_warnings": False,
        "uninterruptible": False,
        "period": 1,
        "offset": 0,
        "time_delta": 1,
        "minTimeDelta": 0,
        "input_delay": 0,
        "output_delay": 0,
        "real_time": False,
        "rt_tolerance": 0.2,
        "rt_lag": 0.2,
        "rt_lead": 0.2,
        "grant_timeout": 0,
        "max_cosim_duration": 0,
        "wait_for_current_time_update": False,
        "restrictive_time_policy": False,
        "slow_responding": False,
        "event_triggered": False,
        # Iteration
        "rollback": False,
        "max_iterations": 50,
        "forward_compute": False,
        # other
        "indexgroup": 0,
        # Network
        "reuse_address": False,
        "noack_connect": False,
        "max_size": 4096,
        "max_count": 256,
        "network_retries": 5,
        "encrypted": False,
        "encryption_config": "encryption_config.json",
        "use_os_port": False,
        "client": False,
        "server": False,
        "local_interface": "",
        "broker_address": "127.0.0.1",
        "broker_port": 22608,
        "broker_name": "",
        "local_port": 8080,
        "port_start": 22608,
        "force": False,
        # Connections
        "publications": [],
        "subscriptions": [],
        "inputs": [],
        "endpoints": [],
        "filters": [],
        "translators": []}
    _var_attr = {
        "key": "",
        "type": "",
        "unit": "",
        "connection_optional": True,
        "connection_required": False,
        "tolerance": 0,
        # "default": based on type,
        # for targets can be singular or plural, if an array must use plural form
        "targets": [],
        # indication the publication should buffer data
        "buffer_data": False,
        "strict_input_type_checking": False,
        "alias": "",
        "ignore_unit_mismatch": False,
        "only_update_on_change": False,
        "only_transmit_on_change": False,
        "info": {}}
    _pub_var = dict(_var_attr)
    _pub_var.update({
        "global": False,
        "tags": {}})
    _sub_var = dict(_var_attr)
    _sub_var.update({})
    _inp_var = dict(_var_attr)
    _inp_var.update({
        "global": False,
        "connections": 1,
        "input_priority_location": 0,
        # possible to have this as a config option
        "clear_priority_list": False,
        "single_connection_only": False,
        "multiple_connections_allowed": True,
        "multi_input_handling_method": "none"})
    _end_pts = {
        "name": "",
        "type": "",
        # endpoint destination "federate/name"
        "destination": "",
        # target is same as destination
        "target": "",
        "alias": "",
        "global": False,
        "subscriptions": "",
        "filters": "",
        "info": {},
        "tags": {}
    }
    _filters = {
        "name": "",
        # use singular for *_targets, use multiples for *Targets
        "source_targets": "",
        "destination_targets": "",
        "sourceTargets": list,
        "destinationTargets": list,
        "info": {},
        "operation": "randomdelay",
        "properties": {
            "name": "delay",
            "value": 600}
    }
    _translators = {
        "name": "",
        "type": "",
        # use singular for *_targets, use multiples for *Targets
        "source_targets": "",
        "destination_targets": "",
        "sourceTargets": list,
        "destinationTargets": list,
        "info": {}}

    def __init__(self, name: str, **kwargs):
        self.name = name

        # Helics attributes for json
        self._cnfg = {}
        self.config("name", name)
        # change log_level to debug, warning, error
        self.config("log_level", "warning")

        self._cnfg.update(kwargs)
        for attr_name, attr in self._cnfg.items():
            HelicsMsg.verify(HelicsMsg._config_var, attr_name, attr)

        self._pubs = []
        self._subs = []
        self._inputs = []
        self._endpoints = []
        self._filters = []
        self._translators = []

    def write_json(self) -> dict:
        """
        Adds publications and subscriptions to the objects "_cnfg" (configuration)
        attribute and returns it as a dictionary.

        Returns:
            dict: Configuration dict after adding publications and subscriptions
        """
        if self._pubs.__len__() > 0: self.config("publications", self._pubs)
        if self._subs.__len__() > 0: self.config("subscriptions", self._subs)
        if self._inputs.__len__() > 0: self.config("inputs", self._inputs)
        if self._endpoints.__len__() > 0: self.config("endpoints", self._endpoints)
        if self._filters.__len__() > 0: self.config("filters", self._filters)
        if self._translators.__len__() > 0: self.config("translators", self._translators)
        return self._cnfg

    def write_file(self, _fn: str) -> None:
        """
        Adds publications and subscriptions to the objects "_cnfg" (configuration)
        attribute and writes it to the specified file.

        Args:
            _fn (str): File name (including path) to which configuration will be written.
        """
        op = open(_fn, 'w', encoding='utf-8')
        json.dump(self.write_json(), op, ensure_ascii=False, indent=2)
        op.close()

    @staticmethod
    def verify(diction: dict, name: str, value: any):
        if name in diction.keys():
            if type(diction[name]) == type(value):
                if diction[name] != value:
                    return True
                else:
                    print(f"The value: '{value}' is the default for '{name}', and does not have to be coded")
                    return True
            else:
                raise ValueError(f"Diction type \'{type(value)}\' not allowed for {name}")
        else:
            raise ValueError(f"Diction flag \'{name}\' not allowed")

    def config(self, _n: str, _v: any) -> dict:
        """
        Adds key specified by first parameter with value specified by the
        second parameter to the config ("_cnfg") attribute of this object

        Args:
            _n (str): Key under which new attribute will be added
            _v (any): Value added to dictionary

        Returns:
            dict: Dictionary to which the new value was added.
        """
        if HelicsMsg.verify(self._config_var, _n, _v):
            self._cnfg[_n] = _v
        return self._cnfg

    def collect(self, collect: Collect) -> None:
        """Todo

        Args:
            collect (Collect): _description_
        """
        self.config("tags", {"logger": collect.value})

    def get_pubs(self):
        return self._pubs

    def publication(self, diction: dict, _c: Collect = None) -> None:
        if type(_c) is Collect: diction["tags"] = {"logger": _c.value}
        for name in diction.keys():
            HelicsMsg.verify(self._pub_var, name, diction[name])
        self._pubs.append(diction)

    def pubs(self, _k: str, _t: str, _o: str, _p: str, _g: bool = True, _c: Collect = None) -> None:
        """
        Defines a HELICS publication definition and adds it to the
        "_pubs" attribute of this object. This API supports the
        definition of the publication "info" field which is used by
        GridLAB-D to link the publication to the GridLAB-D object. This API
        does not include support of the publication "unit" field.

        Args:
            _k (str): HELICS key (name) of publication
            _t (str): HELICS data type of publication
            _o (str): HELICS "info" object name
            _p (str): HELICS "info" object property associate with the name
            _g (bool, optional): Indicates whether publication is global in the HELICS namespace.
                Defaults to True.
            _c (Collect, optional): Collect object used by the logger.
                Defaults to None.
        """
        # for object and property is for internal code interface for GridLAB-D
        diction = {"global": _g, "key": _k, "type": _t, "info": {"object": _o, "property": _p}}
        self.publication(diction, _c)

    def pubs_n(self, _k: str, _t: str, _g: bool = True, _c: Collect = None) -> None:
        """
        Defines a HELICS publication definition and adds it to the
        "_pubs" attribute of this object. Does not include support for the
        "info" field used by GridLAB-D for HELICS configuration. Does not
        include support of the publication "unit" field.

        Args:
            _k (str): HELICS key (name) of publication
            _t (str): HELICS data type of publication
            _g (bool, optional): Indicates whether publication is global in the HELICS namespace.
                Defaults to True.
            _c (Collect, optional): Collect object used by the logger.
                Defaults to None.
        """
        diction = {"global": _g, "key": _k, "type": _t}
        if type(_c) is Collect:
            diction["tags"] = {"logger": _c.value}
        self._pubs.append(diction)

    def pubs_e(self, _k: str, _t: str, _u: str, _g: bool = None, _c: Collect = None) -> None:
        """
        Defines a HELICS publication definition and adds it to the
        "_pubs" attribute of this object. Includes support for the
        publication "unit" field.

        Args:
            _k (str): HELICS key (name) of publication
            _t (str): HELICS data type of publication
            _u (str): HELICS unit of publication
            _g (bool, optional): Indicates whether publication is global in the HELICS namespace.
                Defaults to True.
            _c (Collect, optional): Collect object used by the logger.
                Defaults to None.
        """
        # for object and property is for internal code interface for EnergyPlus
        diction = {"key": _k, "type": _t, "unit": _u}
        if type(_g) is bool:
            diction["global"] = _g
        self.publication(diction, _c)

    def get_subs(self):
        return self._subs

    def subscription(self, diction: dict) -> None:
        for name in diction.keys():
            HelicsMsg.verify(self._sub_var, name, diction[name])
        self._subs.append(diction)

    def subs(self, _k: str, _t: str, _o: str, _p: str) -> None:
        """
        Defines a HELICS subscription definition and adds it to the
        "_subs" attribute of this object. This API supports the
        definition of the subscription "info" field which is used by
        GridLAB-D to link the publication to the GridLAB-D object. This does
        not include support of the subscription "unit" field.

        Args:
            _k (str): HELICS key of subscription indicating which publication
                this subscription is linked to.
            _t (str): HELICS data type of subscription
            _o (str): HELICS "info" object name
            _p (str): HELICS "info" object property associate with the name
        """
        self.subscription({"key": _k, "type": _t, "info": {"object": _o, "property": _p}})

    def subs_n(self, _k, _t) -> None:
        """
        Defines a HELICS subscription definition and adds it to the
        "_subs" attribute of this object. This API does not support the
        subscription "info", "required", or "type" field.

        Args:
            _k (str): HELICS key of subscription indicating which publication
                this subscription is linked to.
            _t (str): HELICS data type of subscription
        """
        self._subs.append({"key": _k, "type": _t})

    def subs_e(self, _k: str, _t: str, _u: str, _r: bool = None) -> None:
        """
        Defines a HELICS subscription definition and adds it to the
        "_subs" attribute of this object. This API supports the
        EnergyPlus to link the subscription to the EnergyPlus object. This
        supports the subscription "connection_required" flag.

        Args:
            _k (str): HELICS key of subscription indicating which publication
                this subscription is linked to.
            _t (str): HELICS data type of subscription
            _u (str): unit name
            _r (bool, optional): HELICS "required" flag. Setting this flag will
                cause HELICS to throw an error if the HELICS subscription does not
                connect to the publication indicated by the "key" field.
                Defaults to None.
        """
        diction = {"key": _k, "type": _t, "unit": _u}
        if type(_r) is bool:
            diction["connection_required"] = _r
        self.subscription(diction)

    def end_point(self, diction: dict, _c: Collect = None) -> None:
        if type(_c) is Collect:
            diction["tags"] = {"logger": _c.value}
        # rename 'key' to 'name'
        if "key" in diction:
            diction["name"] = diction["key"]
            diction.pop("key")
        for name in diction.keys():
            HelicsMsg.verify(self._end_pts, name, diction[name])
        self._endpoints.append(diction)

    def endpt(self, _k: str, _d: list | str, _g: bool = None, _c: Collect = None) -> None:
        diction = {"name": _k, "destination": _d}
        if type(_g) is bool:
            diction["global"] = _g
        self.end_point(diction, _c)

    def subscribe_from_published(self, h_msg: object, varfilter: str):
        if type(h_msg) == HelicsMsg:
            pub_msg = h_msg._pubs
            for v in pub_msg:
                if varfilter in pub_msg[v].key:
                    self.subs_n(pub_msg[v].key, pub_msg[v].type)
