"""
Created on 7/7/2023

@author: Mitch Pelton
mitch.pelton@pnnl.gov
"""

from cosim_toolbox.helicsConfig import Collect
from cosim_toolbox.federation import FederateConfig


class MyFederate(FederateConfig):

    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)

        self.config("federate_type", "value")
        self.config("image", "cosim-cst:latest")
        self.config("prefix", "export WEATHER_CONFIG=test_weather.json")
        self.config("command", f"python3 -c \"import tesp_support.weather.weather_agent as tesp;tesp.startWeatherAgent('weather.dat')\"")
        self.helics.collect(Collect.YES)
