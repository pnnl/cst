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


class Collect(Enum):
    YES = 'yes'
    NO = 'no'
    MAYBE = 'maybe'


class HelicsMsg():
    """Provides a data structure for building up the HELICS configuration
    definitions for publications and subscriptions.
    """

    config_var = {
        # General
        "name": "federate name",
        "core_type": "zmq",
        "core_name": "core name",
        "core_init_string": "",
        "broker_key": "",
        "autobroker": False,
        "connection_required": False,
        "connection_optional": True,
        "strict_input_type_checking": False,
        "terminate_on_error": False,
        "source_only": False,
        "observer": False,
        "dynamic": False,
        "only_update_on_change": False,
        "only_transmit_on_change": False,
        # Logging
        "logfile": "output.log",
        "log_level": "warning",
        "force_logging_flush": False,
        "file_log_level": "",
        "console_log_level": "",
        "dump_log": False,
        "logbuffer": 10,
        # Timing
        "ignore_time_mismatch_warnings": False,
        "uninterruptible": False,
        "period": 0,
        "offset": 0,
        "time_delta": 0,
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
        # Iteration
        "rollback": False,
        "max_iterations": 10,
        "forward_compute": False,
        # other
        "indexgroup": 5,
        # Network
        "interfaceNetwork": "local",
        "brokeraddress": "127.0.0.1",
        "reuse_address": False,
        "noack": False,
        "maxsize": 4096,
        "maxcount": 256,
        "networkretries": 5,
        "osport": False,
        "brokerinit": "",
        "server_mode": "",
        "interface": "(local IP address)",
        "port": 1234,
        "brokerport": 22608,
        "localport": 8080,
        "portstart": 22608,
        "encrypted": False,
        "encryption_config": "encryption_config.json",
        "publications": [],
        "subscriptions": [],
        "inputs": [],
        "endpoints": [],
        "filters": [],
        "translators": []}
    var_attr = {
        "key": "key name",
        "type": "",
        "unit": "m",
        "global": False,
        "connection_optional": True,
        "connection_required": False,
        "tolerance": -1,
        # for targets can be singular or plural, if an array must use plural form
        "targets": "",
        # indication the publication should buffer data
        "buffer_data": False,
        "strict_input_type_checking": False,
        "alias": "",
        "ignore_unit_mismatch": False,
        "info": {}}
    pub_var = dict(var_attr)
    pub_var.update({
        "only_transmit_on_change": False,
        "tags": {}})
    sub_var = dict(var_attr)
    sub_var.update({
        "only_update_on_change": False,
        "require": False,
        "default": any})
    inp_var = dict(var_attr)
    inp_var.update({
        "connections": 1,
        "input_priority_location": 0,
        "clear_priority_list": "possible to have this as a config option?",
        "single_connection_only": False,
        "multiple_connections_allowed": False,
        "multi_input_handling_method": "average",
        # for targets can be singular or plural, if an array must use plural form
        "targets": ["pub1", "pub2"],
        "default": 5.5})
    end_pts = {
        "name": "endpoint key name",
        "type": "endpoint type",
        "global": True,
        "destination": "default endpoint destination",
        "target": "default endpoint destination",
        "alias": "",
        "subscriptions": "",
        "filters": "",
        "info": "",
        "tags": {}
    }
    filters = {
        "name": "filter name",
        "source_targets": "endpoint name",
        "destination_targets": "endpoint name",
        "info": "",
        "operation": "randomdelay",
        "properties": {
            "name": "delay",
            "value": 600}
    }
    translators = {
        "name": "translator name",
        # can use singular form if only a single target
        "source_target": "publication name",
        "destination_targets": "endpoint name",
        "info": "",
        "type": "JSON"}

    def __init__(self, name: str, period: float):
        # change logging to debug, warning, error
        self._pubs = []
        self._subs = []
        self._inputs = []
        self._endpoints = []
        self._filters = []
        self._translators = []
        self._cnfg = {
            "name": name,
            "period": period,
            "logging": "warning"}

    def write_json(self) -> dict:
        """Adds publications and subscriptions to this objects
        "_cnfg" (configuration) attribute and returns it as a
        dictionary.

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
        """Adds publications and subscriptions to this objects
        "_cnfg" (configuration) attribute and writes it to the
        specified file.

        Args:
            _fn (str): File name (including path) to which
            configuration will be written.
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
                raise ValueError(f"Diction type \'{type(value)}\' not allowed for {name}")
        else:
            raise ValueError(f"Diction flag \'{name}\' not allowed")
        return False

    def config(self, _n: str, _v: any) -> dict:
        """Adds key specified by first parameter with value specified
        by the second parameter to the config ("_cnfg") attribute of
        this object

        Args:
            _n (str): Key under which new attribute will added
            _v (any): Value added to dictionary

        Returns:
            dict: Dictionary to which the new value was added.
        """
        if HelicsMsg.verify(self.config_var, _n, _v):
            self._cnfg[_n] = _v
        return self._cnfg

    def collect(self, collect: Collect) -> None:
        """_summary_

        Args:
            collect (Collect): _description_
        """
        self._cnfg["tags"] = {"logger": collect.value}

    def publication(self, diction: dict, _c: Collect = None) -> None:
        if type(_c) is Collect: diction["tags"] = {"logger": _c.value}
        for name in diction.keys():
            HelicsMsg.verify(self.pub_var, name, diction[name])
        self._pubs.append(diction)

    def pubs(self, _k: str, _t: str, _o: str, _p: str, _g: bool = True, _c: Collect = None) -> None:
        """Defines a HELICS publication definition and adds it to the
        "_pubs" attribute of this object. This API supports the
        definition of the publication "info" field which is used by
        GridLAB-D to link the publication to the GridLAB-D object. This API
        does not include support of the publication "unit" field.

        Args:
            _k (str): HELICS key (name) of publication
            _t (str): HELICS data type of publication
            _o (str): HELICS "info" object name
            _p (str): HELICS "info" object property associate with the name
            _g (bool, optional): Indicates whether publication is global in the
            HELICS namespace. Defaults to True.
            _c (Collect, optional): Collect object used by the logger.
            Defaults to None.
        """
        # for object and property is for internal code interface for GridLAB-D
        diction = {"global": _g, "key": _k, "type": _t, "info": {"object": _o, "property": _p}}
        self.publication(diction, _c)

    def pubs_n(self, _k: str, _t: str, _g: bool = True, _c: Collect = None) -> None:
        """Defines a HELICS publication definition and adds it to the
        "_pubs" attribute of this object. Does not include support for the
        "info" field used by GridLAB-D for HELICS configuration. Does not
        include support of the publication "unit" field.

        Args:
            _k (str): HELICS key (name) of publication
            _t (str): HELICS data type of publication
            _g (bool, optional): Indicates whether publication is global in the
            HELICS namespace. Defaults to True.
            _c (Collect, optional): Collect object used by the logger.
            Defaults to None.
        """
        diction = {"global": _g, "key": _k, "type": _t}
        if type(_c) is Collect:
            diction["tags"] = {"logger": _c.value}
        self._pubs.append(diction)

    def pubs_e(self, _k: str, _t: str, _u: str, _g: bool = None, _c: Collect = None) -> None:
        """Defines a HELICS publication definition and adds it to the
        "_pubs" attribute of this object. Includes support for the
        publication "unit" field.

        Args:
            _k (str): HELICS key (name) of publication
            _t (str): HELICS data type of publication
            _u (str): HELICS unit of publication
            _g (bool, optional): Indicates whether publication is global in the
            HELICS namespace. Defaults to True.
            _c (Collect, optional): Collect object used by the logger.
            Defaults to None.
        """
        # for object and property is for internal code interface for EnergyPlus
        diction = {"key": _k, "type": _t, "unit": _u, "global": True}
        if type(_g) is bool: diction["global"] = _g
        self.publication(diction, _c)

    def subscription(self, diction: dict) -> None:
        for name in diction.keys():
            HelicsMsg.verify(self.sub_var, name, diction[name])
        self._subs.append(diction)

    def subs(self, _k: str, _t: str, _o: str, _p: str) -> None:
        """Defines a HELICS subscription definition and adds it to the
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
        # for object and property is for internal code interface for GridLAB-D
        self.subscription({"key": _k, "type": _t, "info": {"object": _o, "property": _p}})

    def subs_n(self, _k, _t) -> None:
        """Defines a HELICS subscription definition and adds it to the
        "_subs" attribute of this object. This API does not support the
        subscription "info", "required", or "type" field.

        Args:
            _k (str): HELICS key of subscription indicating which publication
            this subscription is linked to.
            _t (str): HELICS data type of subscription
        """
        self._subs.append({"key": _k, "type": _t})

    def subs_e(self, _k: str, _t: str, _u: str, _r: bool = None) -> None:
        """Defines a HELICS subscription definition and adds it to the
        "_subs" attribute of this object. This API supports the
        definition of the subscription "info" field which is used by
        GridLAB-D to link the subscription to the GridLAB-D object. This
        supports the subscription "required" flag.

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
        # for object and property is for internal code interface for EnergyPlus
        diction = {"key": _k, "type": _t, "unit": _u, "global": True}
        if type(_r) is bool: diction["require"] = _r
        self.subscription(diction)

    def end_point(self, diction: dict, _c: Collect = None) -> None:
        if type(_c) is Collect: diction["tags"] = {"logger": _c.value}
        for name in diction.keys():
            HelicsMsg.verify(self.end_pts, name, diction[name])
        self._endpoints.append(diction)

    def endpt(self, _k: str, _d: list | str, _g: bool = None, _c: Collect = None) -> None:
        diction = {"name": _k, "destination": _d}
        if type(_g) is bool: diction["global"] = _g
        self.end_point(diction, _c)

    def subscribe_from_published(self, h_msg: object, varfilter: str):
        if type(h_msg) == HelicsMsg:
            pub_msg = h_msg._pubs
            for v in pub_msg:
                if varfilter in pub_msg[v].key:
                    self.subs_n(pub_msg[v].key, pub_msg[v].type)


"""
# filter, scale, index, regex
# define filter for

# https://mepas.pnnl.gov/FramesV1/model.stm
# https://mepas.pnnl.gov/ACC/protocol.htm

What can we learn from these cases 
tesp_case.py
prep_substation_dsot.py

FNCS published only output 

input->module->output(input)->module 
input->module->boundary->module 

Onus on module(federate) developer to read/find(subscribe) inputs 
then manipulate the inputs and publish the outputs.

gui works well because humans are matching machines and can understand context.

Can we infer context, given some filter, when we want to find and subscribe published outputs.

Develop a language to published 'key' into output boundary and then be able to find automagically.

The output should unique and contain 'key' or 'info' for find and match.

In dsot gridlabd indices are: 
      gld_1 = federate
      R4_12_47_1 = feeder
      _tn_1 = transformer
      _Low = income
      _hse_1 = house
      #Tair = property

      "key": "R4_12_47_1_tn_1_Low_hse_1#Tair",
      "info": {
        "object": "R4_12_47_1_tn_1_Low_hse_1",
        "property": "air_temperature" }

      key: feeder
      {R4_12_47_1,sd}  

in energyplus indices
      eplus_1 = federate
      EMS Cooling Controlled Load = property

      agent_1 = federate
      cooling_setpoint_delta = property


"""
