"""
Created on 7/7/2023

@author: Mitch Pelton
mitch.pelton@pnnl.gov
"""

from cosim_toolbox.helicsConfig import Collect
from cosim_toolbox.helicsConfig import HelicsPubGroup
from cosim_toolbox.helicsConfig import HelicsSubGroup
from cosim_toolbox.federation import FederateConfig

class MyFederateMatch(FederateConfig):

    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)

        fmt = {
            "blank": {"fed": "", "keys": ["", ""], "indices": []},
            "gld_7": {"fed": "gld_7"},
            "sub_7": {"fed": "sub_7"}
        }
        self.outputs["pypower1"] = HelicsPubGroup("LMP_7", "double", fmt["blank"])
        self.outputs["pypower2"] = HelicsPubGroup("three_phase_voltage_7", "double", fmt["blank"])

        self.inputs["gridlabd1"] = HelicsSubGroup("distribution_load", "complex", fmt["gld_7"])
        self.inputs["substation1"] = HelicsSubGroup("unresponsive_mw", "double", fmt["sub_7"])
        self.inputs["substation2"] = HelicsSubGroup("responsive_max_mw", "double", fmt["sub_7"])
        self.inputs["substation3"] = HelicsSubGroup("responsive_c2", "double", fmt["sub_7"])
        self.inputs["substation4"] = HelicsSubGroup("responsive_c1", "double", fmt["sub_7"])
        self.inputs["substation5"] = HelicsSubGroup("responsive_deg", "integer", fmt["sub_7"])
        self.inputs["substation6"] = HelicsSubGroup("clear_price", "double", fmt["sub_7"])

        self.config("federate_type", "value")
        self.config("image", "cosim-cst:latest")
        self.config("command", f"python3 -c \"import tesp_support.api.tso_PYPOWER as tesp;tesp.tso_pypower_loop('test_pp.json','test',helicsConfig='{name}.json')\"")
        self.helics.collect(Collect.YES)

class MyFederate(FederateConfig):

    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)

        fmt = {
            "blank": { "fed": "", "keys": ["", ""], "indices": []},
            "load": { "fed": "gld_7", "keys": ["/", ""], "indices": []},
            "bid": { "fed": "sub_7", "keys": ["/", ""], "indices": []}
        }

        self.outputs["pypower1"] = HelicsPubGroup("LMP_7", "double", fmt["blank"])
        self.outputs["pypower2"] = HelicsPubGroup("three_phase_voltage_7", "double", fmt["blank"])

        self.inputs["gridlabd1"] = HelicsSubGroup("distribution_load", "complex", fmt["load"])
        self.inputs["substation1"] = HelicsSubGroup("unresponsive_mw", "double", fmt["bid"])
        self.inputs["substation2"] = HelicsSubGroup("responsive_max_mw", "double", fmt["bid"])
        self.inputs["substation3"] = HelicsSubGroup("responsive_c2", "double", fmt["bid"])
        self.inputs["substation4"] = HelicsSubGroup("responsive_c1", "double", fmt["bid"])
        self.inputs["substation5"] = HelicsSubGroup("responsive_deg", "integer", fmt["bid"])
        self.inputs["substation6"] = HelicsSubGroup("clear_price", "double", fmt["bid"])

        self.config("federate_type", "value")
        self.config("image", "cosim-cst:latest")
        self.config("command", f"python3 -c \"import tesp_support.api.tso_PYPOWER as tesp;tesp.tso_pypower_loop('test_pp.json','test',helicsConfig='{name}.json')\"")
        self.helics.collect(Collect.YES)
