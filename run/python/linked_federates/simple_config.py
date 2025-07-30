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

        self.outputs["current1"] = HelicsPubGroup("current", "double", fmt["bt"], unit="A", globl=True, tags={"logger": Collect.YES.value})
        self.outputs["current2"] = HelicsPubGroup("current2", "integer", fmt["bt"], unit="A", globl=True, tags={"logger": Collect.NO.value})
        self.outputs["current3"] = HelicsPubGroup("current3", "boolean", fmt["blank"], unit="A")
        self.outputs["current4"] = HelicsPubGroup("current4", "string", fmt["blank"], unit="A")
        self.outputs["current5"] = HelicsPubGroup("current5", "complex", fmt["bt"], unit="A", globl=True, tags={"logger": Collect.MAYBE.value})
        self.outputs["current6"] = HelicsPubGroup("current6", "vector", fmt["bt"], unit="A", globl=True, tags={"logger": Collect.NO.value})

        self.inputs["voltage1"] = HelicsSubGroup("voltage", "double", fmt["ev"], unit="V")
        self.inputs["voltage2"] = HelicsSubGroup("voltage2", "integer", fmt["ev"], unit="V")
        self.inputs["voltage3"] = HelicsSubGroup("voltage3", "boolean", fmt["ev"], unit="V")
        self.inputs["voltage4"] = HelicsSubGroup("voltage4", "string", fmt["ev"], unit="V")
        self.inputs["voltage5"] = HelicsSubGroup("voltage5", "complex", fmt["ev"], unit="V")
        self.inputs["voltage6"] = HelicsSubGroup("voltage6", "vector", fmt["ev"], unit="V")

        self.endpoints["endpoint1"] = HelicsEndPtGroup("current1", fmt["bt"], "voltage1", fmt["ev"], globl=True, tags={"logger": Collect.YES.value})

        self.config("federate_type", "combo")
        self.helics.collect(Collect.YES)
