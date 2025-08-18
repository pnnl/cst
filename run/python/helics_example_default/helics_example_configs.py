"""
Created on 8/6/2025


@author: Trevor Hardy
trevor.hardy@pnnl.gov
"""

from cosim_toolbox.helicsConfig import Collect
from cosim_toolbox.federation import FederateConfig


class BatteryFederateConfig(FederateConfig):

    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)

        self.config("federate_type", "value")
        self.config("image", "cosim-cst:latest")
        self.config("command", f"python3  \"battery.py\"")
        self.helics.collect(Collect.YES)

class ChargerFederateConfig(FederateConfig):

    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)

        self.config("federate_type", "value")
        self.config("image", "cosim-cst:latest")
        self.config("command", f"python3  \"charger.py\"")
        self.helics.collect(Collect.YES)