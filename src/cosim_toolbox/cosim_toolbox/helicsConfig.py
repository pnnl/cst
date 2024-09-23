from enum import Enum
import json


class Collect(Enum):
    YES = 'yes'
    NO = 'no'
    MAYBE = 'maybe'


class HelicsMsg(object):

    def __init__(self, name: str, period: float):
        # change logging to debug, warning, error
        self._subs = []
        self._pubs = []
        self._cnfg = {"name": name,
                      "period": period,
                      "logging": "warning",
                      }

    def write_json(self) -> dict:
        self.config("publications", self._pubs)
        self.config("subscriptions", self._subs)
        return self._cnfg

    def write_file(self, _fn: str) -> None:
        self.config("publications", self._pubs)
        self.config("subscriptions", self._subs)
        op = open(_fn, 'w', encoding='utf-8')
        json.dump(self._cnfg, op, ensure_ascii=False, indent=2)
        op.close()

    def config(self, _n: str, _v: any) -> dict:
        self._cnfg[_n] = _v
        return self._cnfg

    def collect(self, collect: Collect) -> None:
        self._cnfg["tags"] = {"logger": collect.value}

    def pubs(self, _k: str, _t: str, _o: str, _p: str, _g: bool = True, _c: Collect = None) -> None:
        # for object and property is for internal code interface for GridLAB-D
        diction = {"global": True, "key": _k, "type": _t, "info": {"object": _o, "property": _p}}
        if type(_c) is Collect:
            diction["tags"] = {"logger": _c.value}
        self._pubs.append(diction)

    def pubs_n(self, _k: str, _t: str, _g: bool = True, _c: Collect = None) -> None:
        diction = {"global": True, "key": _k, "type": _t}
        if type(_c) is Collect:
            diction["tags"] = {"logger": _c.value}
        self._pubs.append(diction)

    def pubs_e(self, _k: str, _t: str, _u: str, _g: bool = None, _c: Collect = None) -> None:
        # for object and property is for internal code interface for EnergyPlus
        diction = {"global": True, "key": _k, "type": _t, "unit": _u}
        if type(_g) is bool:
            diction["global"] = _g
        if type(_c) is Collect:
            diction["tags"] = {"logger": _c.value}
        self._pubs.append(diction)

    def subs(self, _k: str, _t: str, _o: str, _p: str) -> None:
        # for object and property is for internal code interface for GridLAB-D
        self._subs.append({"key": _k, "type": _t, "info": {"object": _o, "property": _p}})

    def subs_e(self, _k: str, _t: str, _i: str, _r: bool = None) -> None:
        # for object and property is for internal code interface for EnergyPlus
        diction = {"key": _k, "type": _t, "require": True, "info": _i}
        if type(_r) is bool:
            diction["require"] = _r
        self._subs.append(diction)

    def subs_n(self, _k, _t) -> None:
        self._subs.append({"key": _k, "type": _t})
