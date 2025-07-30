"""
Created on 7/7/2023

@author: Mitch Pelton
mitch.pelton@pnnl.gov
"""

from cosim_toolbox.helicsConfig import Collect
from cosim_toolbox.helicsConfig import HelicsPubGroup
from cosim_toolbox.helicsConfig import HelicsSubGroup
from cosim_toolbox.helicsConfig import HelicsEndPtGroup
from cosim_toolbox.federation import FederateConfig


class MyFederate(FederateConfig):

    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)

        fmt = {
            "blank": {"fed": "",
                      "keys": ["", ""],
                      "indices": []},
            "bt": {"fed": "Battery",
                   "keys": ["/", ""],
                   "indices": []},
            "ev": {"fed": "EVehicle",
                   "keys": ["/", ""],
                   "indices": []}
        }

        self.outputs["voltage1"] = HelicsPubGroup("voltage", "double", fmt["blank"], unit="V")
        self.outputs["voltage2"] = HelicsPubGroup("voltage2", "integer", fmt["blank"], unit="V")
        self.outputs["voltage3"] = HelicsPubGroup("voltage3", "boolean", fmt["ev"], unit="V", globl=True, tags={"logger": Collect.NO.value})
        self.outputs["voltage4"] = HelicsPubGroup("voltage4", "string", fmt["blank"], unit="V")
        self.outputs["voltage5"] = HelicsPubGroup("voltage5", "complex", fmt["blank"], unit="V")
        self.outputs["voltage6"] = HelicsPubGroup("voltage6", "vector", fmt["blank"], unit="V")

        self.inputs["current1"] = HelicsSubGroup("current", "double", fmt["bt"], unit="A")
        self.inputs["current2"] = HelicsSubGroup("current2", "integer", fmt["bt"], unit="A")
        self.inputs["current3"] = HelicsSubGroup("current3", "boolean", fmt["bt"], unit="A")
        self.inputs["current4"] = HelicsSubGroup("current4", "string", fmt["bt"], unit="A")
        self.inputs["current5"] = HelicsSubGroup("current5", "complex", fmt["bt"], unit="A")
        self.inputs["current6"] = HelicsSubGroup("current6", "vector", fmt["bt"], unit="A")

        self.endpoints["endpoint1"] = HelicsEndPtGroup("voltage1", fmt["blank"], "current1", fmt["bt"], tags={"logger": Collect.YES.value})

        self.config("federate_type", "combo")
        self.helics.collect(Collect.NO)
