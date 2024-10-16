from enum import Enum
import json


class Collect(Enum):
    YES = 'yes'
    NO = 'no'
    MAYBE = 'maybe'


class HelicsMsg():
    """Provides a data structure for building up the HELICS configuration
    definitions for pubblications and subscriptions.

    TODO: Need to add support for endpoints.

    """
    def __init__(self, name: str, period: float):
        # change logging to debug, warning, error
        self._subs = []
        self._pubs = []
        self._cnfg = {"name": name,
                      "period": period,
                      "logging": "warning",
                      }

    def write_json(self) -> dict:
        """Adds publications and subscriptions to this objects 
        "_cnfg" (configuration) attribute and returns it as a 
        dictionary.

        TODO: Add endpoints as well (maybe?).

        Returns:
            dict: Configuration dict after adding publications and subscriptions
        """
        self.config("publications", self._pubs)
        self.config("subscriptions", self._subs)
        return self._cnfg

    def write_file(self, _fn: str) -> None:
        """Adds publications and subscriptions to this objects 
        "_cnfg" (configuration) attribute and writes it to the 
        specified file.

        Args:
            _fn (str): File name (including path) to which 
            configuration will be written.
        """
        self.config("publications", self._pubs)
        self.config("subscriptions", self._subs)
        op = open(_fn, 'w', encoding='utf-8')
        json.dump(self._cnfg, op, ensure_ascii=False, indent=2)
        op.close()

    def config(self, _n: str, _v: any) -> dict:
        """Adds key specied by first parameter with value specified
        by the second paramter to the config ("_cnfg") attribute of
        this object

        Args:
            _n (str): Key under which new attribute will added
            _v (any): Value added to dictionary

        Returns:
            dict: Dictionary to which the new value was added.
        """
        self._cnfg[_n] = _v
        return self._cnfg

    def collect(self, collect: Collect) -> None:
        """_summary_

        Args:
            collect (Collect): _description_
        """
        self._cnfg["tags"] = {"logger": collect.value}

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
            _p (str): HELICS "info" object property associate with the "info" 
            name
            _g (bool, optional): Indicates whether publication is global in the
            HELICS namespace. Defaults to True.
            _c (Collect, optional): Collect object used by the logger. 
            Defaults to None.
        """
        # for object and property is for internal code interface for GridLAB-D
        diction = {"global": True, "key": _k, "type": _t, "info": {"object": _o, "property": _p}}
        if type(_c) is Collect:
            diction["tags"] = {"logger": _c.value}
        self._pubs.append(diction)

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
        diction = {"global": True, "key": _k, "type": _t}
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
        diction = {"global": True, "key": _k, "type": _t, "unit": _u}
        if type(_g) is bool:
            diction["global"] = _g
        if type(_c) is Collect:
            diction["tags"] = {"logger": _c.value}
        self._pubs.append(diction)

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
            _p (str): HELICS "info" object property associate with the "info"
            name
        """
        # for object and property is for internal code interface for GridLAB-D
        self._subs.append({"key": _k, "type": _t, "info": {"object": _o, "property": _p}})

    def subs_e(self, _k: str, _t: str, _i: str, _r: bool = None) -> None:
        """Defines a HELICS subscription definition and adds it to the 
        "_subs" attribute of this object. This API supports the 
        definition of the subscription "info" field which is used by
        GridLAB-D to link the subscription to the GridLAB-D object. This 
        supports the subscription "required" flag.

        Args:
            _k (str): HELICS key of subscription indicating which publication
            this subscription is linked to.
            _t (str): HELICS data type of subscription
            _i (str): HELICS "info" object
            _r (bool, optional): HELICS "required" flag. Setting this flag will
            cause HELICS to throw an error if the HELICS subscription does not
            connect to the publication indicated by the "key" field. 
            Defaults to None.
        """
        # for object and property is for internal code interface for EnergyPlus
        diction = {"key": _k, "type": _t, "require": True, "info": _i}
        if type(_r) is bool:
            diction["require"] = _r
        self._subs.append(diction)

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
