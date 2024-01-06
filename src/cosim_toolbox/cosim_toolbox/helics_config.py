
import json


class HelicsMsg(object):

    def __init__(self, name, period):
        # change logging to debug, warning, error
        self._subs = []
        self._pubs = []
        self._cnfg = {"name": name,
                      "period": period,
                      "logging": "warning",
                      }
        pass

    def write_json(self):
        self.config("publications", self._pubs)
        self.config("subscriptions", self._subs)
        return self._cnfg

    def write_file(self, _fn):
        self.config("publications", self._pubs)
        self.config("subscriptions", self._subs)
        op = open(_fn, 'w', encoding='utf-8')
        json.dump(self._cnfg, op, ensure_ascii=False, indent=2)
        op.close()

    def config(self, _n, _v):
        self._cnfg[_n] = _v
        return self._cnfg

    def pubs(self, _g, _k, _t, _o, _p):
        # for object and property is for internal code interface for GridLAB-D
        self._pubs.append({"global": _g, "key": _k, "type": _t, "info": {"object": _o, "property": _p}})

    def pubs_n(self, _g, _k, _t):
        self._pubs.append({"global": _g, "key": _k, "type": _t})

    def pubs_e(self, _g, _k, _t, _u):
        # for object and property is for internal code interface for EnergyPlus
        self._pubs.append({"global": _g, "key": _k, "type": _t, "unit": _u})

    def subs(self, _k, _t, _o, _p):
        # for object and property is for internal code interface for GridLAB-D
        self._subs.append({"key": _k, "type": _t, "info": {"object": _o, "property": _p}})

    def subs_e(self, _r, _k, _t, _i):
        # for object and property is for internal code interface for EnergyPlus
        self._subs.append({"key": _k, "type": _t, "require": _r, "info": _i})

    def subs_n(self, _k, _t):
        self._subs.append({"key": _k, "type": _t})
