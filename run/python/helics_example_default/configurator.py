"""
Created on 8/6/2025

@author: Trevor Hardy
trevor.hardy@pnnl.gov
"""

import gridlabd_output
import substation_output
import pypower_output
import weather_output
from cosim_toolbox.federation import FederateConfig
from cosim_toolbox.federation import FederationConfig
from cosim_toolbox.dockerRunner import DockerRunner

def define_federation_list():
    """
    Dictionary defining the data exchange between federates



    """

    voltage_signal = {
        "src": {
            "from_fed": "Charger",
            "keys": ["",""]
        },
        "des": {
            "to_fed": "Charger",
            "keys": ["",""]

        }
    }
        
    bid = {"src": {"from_fed": names[1],
                    "keys": ["", ""],
                    "indices": []},
            "des": [{"to_fed": names[2],
                        "from_fed": names[1],
                        "keys": ["", ""],
                        "indices": []}]}