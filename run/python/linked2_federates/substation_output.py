"""
Created on 7/7/2023

@author: Mitch Pelton
mitch.pelton@pnnl.gov
"""

from cosim_toolbox.helicsConfig import Collect
from cosim_toolbox.helicsConfig import HelicsPubGroup
from cosim_toolbox.helicsConfig import HelicsSubGroup
from cosim_toolbox.federation import FederateConfig
from tesp_support.api.modify_GLM import GLMModifier

class MyFederateMatch(FederateConfig):

    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)

        fmt = {
            "blank": { "fed": "", "keys": ["", ""], "indices": []},
            "pypower": {"fed": "pypower"},
            "gld_7": {"fed": "gld_7"}
        }
        gld_fmt = MyFederateMatch.get_names("test.glm")
        self.outputs["substation1"] = HelicsPubGroup("unresponsive_mw", "double", fmt["blank"])
        self.outputs["substation2"] = HelicsPubGroup("responsive_max_mw", "double", fmt["blank"])
        self.outputs["substation3"] = HelicsPubGroup("responsive_c2", "double", fmt["blank"])
        self.outputs["substation4"] = HelicsPubGroup("responsive_c1", "double", fmt["blank"])
        self.outputs["substation5"] = HelicsPubGroup("responsive_deg", "integer", fmt["blank"])
        self.outputs["substation6"] = HelicsPubGroup("clear_price", "double", fmt["blank"])

        self.outputs["substation7"] = HelicsPubGroup("cooling_setpoint", "double", gld_fmt["hvac"])
        self.outputs["substation8"] = HelicsPubGroup("heating_setpoint", "double", gld_fmt["hvac"])
        self.outputs["substation9"] = HelicsPubGroup("thermostat_deadband", "double", gld_fmt["hvac"])
        self.outputs["substation10"] = HelicsPubGroup("bill_mode", "string", gld_fmt["billing"])
        self.outputs["substation11"] = HelicsPubGroup("price", "double", gld_fmt["billing"])
        self.outputs["substation13"] = HelicsPubGroup("monthly_fee", "double", gld_fmt["billing"])

        self.inputs["pypower1"] = HelicsSubGroup("LMP_7", "double", fmt["pypower"])
        self.inputs["gridlabd1"] = HelicsSubGroup("distribution_load", "complex", fmt["gld_7"])
        self.inputs["gridlabd2"] = HelicsSubGroup("power_state", "string", fmt["gld_7"])
        self.inputs["gridlabd3"] = HelicsSubGroup("air_temperature", "double", fmt["gld_7"])
        self.inputs["gridlabd4"] = HelicsSubGroup("hvac_load", "double", fmt["gld_7"])
        self.inputs["gridlabd5"] = HelicsSubGroup("measured_voltage_1", "complex", fmt["gld_7"])

        self.config("federate_type", "value")
        self.config("image", "cosim-cst:latest")
        self.config("command",f"python3 -c \"import tesp_support.api.substation as tesp;tesp.substation_loop('test_agent_dict.json','test',helicsConfig='{name}.json')\"")
        self.helics.config("uninterruptible", True)
        self.helics.config("only_update_on_change", True)
        self.helics.config("only_transmit_on_change", True)
        self.helics.collect(Collect.YES)

    @staticmethod
    def get_names(path: str) -> dict:
        my_glm = GLMModifier()
        glm, success = my_glm.read_model(path)
        if not success:
            print(f'{path} not found or file not supported; exiting')
        fmt = {
            "hvac": { "fed": "", "keys": ["@list@/", ""], "indices": []},
            "billing": { "fed": "", "keys": ["@list@/", ""], "indices": []}
        }
        for name, attr in glm.house.items():
            if 'ELECTRIC' in attr["cooling_system_type"]:
                fmt["hvac"]["indices"].append(name)
                fmt["billing"]["indices"].append(name + "/" + attr["parent"])
        return fmt

class MyFederate(FederateConfig):

    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)

        fmt = {
            "blank": { "fed": "",
                       "keys": ["", ""],
                       "indices": []},
            "hvac": { "fed": "",
                      "keys": ["Fdr1_Houses_@@_hse_##/", ""],
                      "indices": [["A",1,501], ["B",1,501], ["C",1,501]]},
            "billing": { "fed": "",
                         "keys": ["Fdr1_Houses_@@_hse_##/Fdr1_Houses_@@_mhse_##/", ""],
                         "indices": [["A",1,501], ["B",1,501], ["C",1,501]]},
            "lmp": { "fed": "pypower",
                     "keys": ["/", ""],
                     "indices": []},
            "load": { "fed": "gld_7",
                      "keys": ["/", ""],
                      "indices": []},
            "house": { "fed": "gld_7",
                       "keys": ["/Fdr1_Houses_@@_hse_##/", ""],
                       "indices": [["A", 1, 501], ["B", 1, 501], ["C", 1, 501]]},
            "meter": { "fed": "gld_7",
                       "keys": ["/Fdr1_Houses_@@_mhse_##/", ""],
                       "indices": [["A", 1, 501], ["B", 1, 501], ["C", 1, 501]]},
        }

        self.outputs["substation1"] = HelicsPubGroup("unresponsive_mw", "double", fmt["blank"])
        self.outputs["substation2"] = HelicsPubGroup("responsive_max_mw", "double", fmt["blank"])
        self.outputs["substation3"] = HelicsPubGroup("responsive_c2", "double", fmt["blank"])
        self.outputs["substation4"] = HelicsPubGroup("responsive_c1", "double", fmt["blank"])
        self.outputs["substation5"] = HelicsPubGroup("responsive_deg", "integer", fmt["blank"])
        self.outputs["substation6"] = HelicsPubGroup("clear_price", "double", fmt["blank"])
        self.outputs["substation7"] = HelicsPubGroup("cooling_setpoint", "double", fmt["hvac"])
        self.outputs["substation8"] = HelicsPubGroup("heating_setpoint", "double", fmt["hvac"])
        self.outputs["substation9"] = HelicsPubGroup("thermostat_deadband", "double", fmt["hvac"])
        self.outputs["substation10"] = HelicsPubGroup("bill_mode", "string", fmt["billing"])
        self.outputs["substation11"] = HelicsPubGroup("price", "double", fmt["billing"])
        self.outputs["substation12"] = HelicsPubGroup("monthly_fee", "double", fmt["billing"])

        self.inputs["pypower1"] = HelicsSubGroup("LMP_7", "double", fmt["lmp"])
        self.inputs["gridlabd1"] = HelicsSubGroup("distribution_load", "complex", fmt["load"])
        self.inputs["gridlabd2"] = HelicsSubGroup("power_state", "string", fmt["house"])
        self.inputs["gridlabd3"] = HelicsSubGroup("air_temperature", "double", fmt["house"])
        self.inputs["gridlabd4"] = HelicsSubGroup("hvac_load", "double", fmt["house"])
        self.inputs["gridlabd5"] = HelicsSubGroup("measured_voltage_1", "complex", fmt["meter"])

        self.config("federate_type", "value")
        self.config("image", "cosim-cst:latest")
        self.config("command",f"python3 -c \"import tesp_support.api.substation as tesp;tesp.substation_loop('test_agent_dict.json','test',helicsConfig='{name}.json')\"")
        self.helics.config("uninterruptible", True)
        self.helics.config("only_update_on_change", True)
        self.helics.config("only_transmit_on_change", True)
        self.helics.collect(Collect.YES)

if __name__ == "__main__":
    # myFed = MyFederate('sub_7', period=15)
    myFed = MyFederateMatch('sub_7', period=15)
