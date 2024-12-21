# -*- coding: utf-8 -*-
import helics as h
# import time
# import struct
import matplotlib.pyplot as plt
import logging
import numpy as np
from cosim_toolbox.federate import Federate
import json

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

class Controller(Federate):
    def on_start(self):
        self.n3_va = []
        self.n5_va = []
        self.sw23_p = []
        self.sw45_p = []

    def update_internal_model(self):
        logger.debug("data_from_federation")
        logger.debug(self.data_from_federation)
        self.n3_va.append(abs(self.data_from_federation["inputs"]["node_3_A"]))
        self.n5_va.append(abs(self.data_from_federation["inputs"]["node_5_A"]))
        self.sw23_p.append(self.data_from_federation["inputs"]["switch_2_3"].imag)
        self.sw45_p.append(self.data_from_federation["inputs"]["switch_4_5"].imag)
        if self.current_time == 3600:
            self.hfed.publications["node_3_load_A"].publish(400000.0 + 0j)
            self.hfed.publications["node_3_load_B"].publish(400000.0 + 0j)
            self.hfed.publications["node_3_load_C"].publish(400000.0 + 0j)
        if self.current_time == 7200:
            self.hfed.publications["node_3_load_A"].publish(400000.0 + 50000j)
            self.hfed.publications["node_3_load_B"].publish(400000.0 + 50000j)
            self.hfed.publications["node_3_load_C"].publish(400000.0 + 50000j)
            # self.data_to_federation["publications"]["node_3_load_A"] = 400000.0 + 0j
            # self.data_to_federation["publications"]["node_3_load_B"] = 400000.0 + 0j
            # self.data_to_federation["publications"]["node_3_load_C"] = 400000.0 + 0j
        logger.debug("~~~~~~~~~~~~ data_to_federation ~~~~~~~~~~~~")
        # logger.debug(json.dumps(self.data_to_federation, indent=4))

if __name__ == "__main__":
    _scenario_name = "gld2"
    fed = Controller(fed_name="ctr")
    fed.run(_scenario_name)
