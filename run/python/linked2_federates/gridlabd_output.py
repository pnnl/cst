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
            "load": { "fed": "", "keys": ["", "network_node"], "indices": []},
            "weather": {"fed": "localWeather", "keys": ["/#", "localWeather"], "indices": []},
            "voltage": {"fed": "pypower", "keys": ["/@@", "network_node"],
                        "indices": [["three_phase_voltage_7", True]]},
            "sub_7": {"fed": "sub_7"}
        }
        gld_fmt = self.get_names("test.glm")
        self.outputs["gridlabd1"] = HelicsPubGroup("distribution_load", "complex", fmt["load"])
        self.outputs["gridlabd2"] = HelicsPubGroup("power_state", "string", gld_fmt["house"])
        self.outputs["gridlabd3"] = HelicsPubGroup("air_temperature", "double", gld_fmt["house"])
        self.outputs["gridlabd4"] = HelicsPubGroup("hvac_load", "double", gld_fmt["house"])
        self.outputs["gridlabd5"] = HelicsPubGroup("measured_voltage_1", "complex", gld_fmt["meter"])

        self.inputs["weather1"] = HelicsSubGroup("temperature", "double", fmt["weather"])
        self.inputs["weather2"] = HelicsSubGroup("humidity", "double", fmt["weather"])
        self.inputs["weather3"] = HelicsSubGroup("solar_direct", "double", fmt["weather"])
        self.inputs["weather4"] = HelicsSubGroup("solar_diffuse", "double", fmt["weather"])
        self.inputs["weather5"] = HelicsSubGroup("pressure", "double", fmt["weather"])
        self.inputs["weather6"] = HelicsSubGroup("wind_speed", "double", fmt["weather"])

        self.inputs["pypower"] = HelicsSubGroup("positive_sequence_voltage", "double", fmt["voltage"])
        self.inputs["substation1"] = HelicsSubGroup("cooling_setpoint", "double", fmt["sub_7"])
        self.inputs["substation2"] = HelicsSubGroup("heating_setpoint", "double", fmt["sub_7"])
        self.inputs["substation3"] = HelicsSubGroup("thermostat_deadband", "double", fmt["sub_7"])
        self.inputs["substation4"] = HelicsSubGroup("bill_mode", "string", fmt["sub_7"])
        self.inputs["substation5"] = HelicsSubGroup("price", "double", fmt["sub_7"])
        self.inputs["substation6"] = HelicsSubGroup("monthly_fee", "double", fmt["sub_7"])

        self.config("federate_type", "value")
        self.config("image", "cosim-cst:latest")
        self.config("command", f"gridlabd -D USE_HELICS -D METRICS_FILE=test_metrics.json test.glm")
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
            "house": { "fed": "", "keys": ["@list@#", "@list@"], "indices": []},
            "meter": { "fed": "", "keys": ["@list@#", "@list@"], "indices": []}
        }
        for name, attr in glm.house.items():
            if 'ELECTRIC' in attr["cooling_system_type"]:
                fmt["house"]["indices"].append(name)
                fmt["meter"]["indices"].append(attr["parent"])
        return fmt

class MyFederate(FederateConfig):

    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)

        fmt = {
            "load": { "fed": "",
                      "keys": ["", "network_node"],
                      "indices": []},
            "house": { "fed": "",
                       "keys": ["Fdr1_Houses_@@_hse_##/", "Fdr1_Houses_@@_hse_##"],
                       "indices": [["A",1,501], ["B",1,501], ["C",1,501]]},
            "meter": { "fed": "",
                       "keys": ["Fdr1_Houses_@@_mhse_##/", "Fdr1_Houses_@@_mhse_##"],
                       "indices": [["A",1,501], ["B",1,501], ["C",1,501]]},
            "voltage": { "fed": "pypower",
                         "keys": ["/@@", "network_node"],
                         "indices": [["three_phase_voltage_7", True]]},
            "hvac": { "fed": "sub_7",
                      "keys": ["/Fdr1_Houses_@@_hse_##/", "Fdr1_Houses_@@_hse_##"],
                      "indices": [["A",1,501], ["B",1,501], ["C",1,501]]},
            "billing": { "fed": "sub_7",
                         "keys": ["/Fdr1_Houses_@@_hse_##/Fdr1_Houses_@@_mhse_##/", "Fdr1_Houses_@@_mhse_##"],
                         "indices": [["A",1,501], ["B",1,501], ["C",1,501]]},
            "weather": { "fed": "localWeather",
                         "keys": ["/#", "localWeather"],
                         "indices": []}
        }
        self.outputs["gridlabd1"] = HelicsPubGroup("distribution_load", "complex", fmt["load"])
        self.outputs["gridlabd2"] = HelicsPubGroup("power_state", "string", fmt["house"])
        self.outputs["gridlabd3"] = HelicsPubGroup("air_temperature", "double", fmt["house"])
        self.outputs["gridlabd4"] = HelicsPubGroup("hvac_load", "double", fmt["house"])
        self.outputs["gridlabd5"] = HelicsPubGroup("measured_voltage_1", "complex", fmt["meter"])

        self.inputs["pypower1"] = HelicsSubGroup("positive_sequence_voltage", "complex", fmt["voltage"])
        self.inputs["substation1"] = HelicsSubGroup("cooling_setpoint", "double", fmt["hvac"])
        self.inputs["substation2"] = HelicsSubGroup("heating_setpoint", "double", fmt["hvac"])
        self.inputs["substation3"] = HelicsSubGroup("thermostat_deadband", "double", fmt["hvac"])
        self.inputs["substation4"] = HelicsSubGroup("bill_mode", "string", fmt["billing"])
        self.inputs["substation5"] = HelicsSubGroup("price", "double", fmt["billing"])
        self.inputs["substation6"] = HelicsSubGroup("monthly_fee", "double", fmt["billing"])

        self.inputs["weather1"] = HelicsSubGroup("temperature", "double", fmt["weather"])
        self.inputs["weather2"] = HelicsSubGroup("humidity", "double", fmt["weather"])
        self.inputs["weather3"] = HelicsSubGroup("solar_direct", "double", fmt["weather"])
        self.inputs["weather4"] = HelicsSubGroup("solar_diffuse", "double", fmt["weather"])
        self.inputs["weather5"] = HelicsSubGroup("pressure", "double", fmt["weather"])
        self.inputs["weather6"] = HelicsSubGroup("wind_speed", "double", fmt["weather"])

        self.config("federate_type", "value")
        self.config("image", "cosim-cst:latest")
        self.config("command", f"gridlabd -D USE_HELICS -D METRICS_FILE=test_metrics.json test.glm")
        self.helics.config("only_update_on_change", True)
        self.helics.config("only_transmit_on_change", True)
        self.helics.collect(Collect.YES)

if __name__ == "__main__":
    # myFed = MyFederate('gld_7', period=15)
    myFed = MyFederateMatch('gld_7', period=15)
