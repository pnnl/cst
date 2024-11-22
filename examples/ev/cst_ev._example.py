"""
Created 20 Nov 2024

EV federate based on CST Federate class

For use in the CST EV charging federation example.

@author Trevor Hardy
"""

import sys
import logging
import numpy as np
import argparse

from cosim_toolbox.federate import Federate
from cosim_toolbox.dataLogger import DataLogger
from cosim_toolbox.helicsConfig import HelicsMsg

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.ERROR)

class CSTEV(Federate):
    """Simple model of EV battery charging where, for the purposes of
    determining the charging behavior of the EV, the battery is modeled as a
    resistor whose values is a function of state-of-charge SOC. This 
    battery resistance is linear interpolated based on the SOC using fixed
    resistance limits defined in the "effective_R" attribute of this object.


    Args:
        Federate (_type_): _description_
    """

    def __init__(self, fed_name: str = "", **kwargs):
        super().__init__(fed_name, **kwargs)
        self.battery_capacity = 70 # kWh
        self.charging_voltage = 120 # V
        self.charging_current = 10 # A
        self.soc = 0.01
        self.battery_R = 150 # Ohms
        self.socs = np.array([0,1])
        self.effective_R = np.array([8,150])
        self.__dict__.update(kwargs)
        self.subscription = "charging_voltage"
        self.publication = "charging_current"
        self.hConfig = HelicsMsg(self.federate_name, self.time_step)
        self.hConfig.config("core_type", "zmq")
        self.hConfig.config("log_level", "warning")
        self.hConfig.config("terminate_on_error", True)
        self.hConfig.config("wait_for_current_time_update", True)
        if self.scenario["docker"]:
            self.hConfig.config("brokeraddress", "10.5.0.2")
        self.hconfig = self.hConfig.subs(
            self.subscription,
            "double",
        )
        self.hconfig = self.hConfig.pubs(
            self.publication,
            "double",
            True,
            self.hConfig.Collect.YES
        )


    def update_internal_model(self):
        # Get inputs from federation
        self.charging_voltage = self.data_from_federation["inputs"][self.subscription]

        # Update model of EV battery 
        self.battery_R = np.interp(self.soc, self.socs, self.effective_R)
        if self.SOC >= 1:
            self.charging_current = 0
        else:
            self.charging_current = self.charging_voltage / self.battery_R
        added_energy_kWh = (self.charging_current * self.charging_voltage * self.time_step / 3600) /1000 
        self.soc = self.soc + added_energy_kWh

        # Send out new data to the federation
        self.data_to_federation["publications"][self.publication] = self.charging_current

class CSTCharger(Federate):
    """Simple model of an EV charging the regulates the charging current to 
    stay below the physical limits of the device by adjusting the charging 
    voltage between specified limits. Each time step the charger looks at the
    charging current and moves it up or down a few percent to get it into the
    valid charging curent limits.


    Args:
        Federate (_type_): _description_
    """
    def __init__(self, fed_name: str = "", **kwargs):
        super().__init__(fed_name, **kwargs)
        self.charging_voltage = 120 # V
        self.charging_current = 10 # A
        self.max_charging_voltage = 240 # V
        self.min_charging_voltage = 120 # V
        self.max_charging_current = 50 # A
        self.__dict__.update(kwargs)
        self.subscription = "charging_current"
        self.publication = "charging_voltage"
        self.hConfig = HelicsMsg(self.federate_name, self.time_step)
        self.hConfig.config("core_type", "zmq")
        self.hConfig.config("log_level", "warning")
        self.hConfig.config("terminate_on_error", True)
        self.hConfig.config("wait_for_current_time_update", False)
        if self.scenario["docker"]:
            self.hConfig.config("brokeraddress", "10.5.0.2")
        self.hconfig = self.hConfig.subs(
            self.subscription,
            "double",
        )
        self.hconfig = self.hConfig.pubs(
            self.publication,
            "double",
            True,
            self.hConfig.Collect.YES
        )

    def update_internal_model(self):
        # Get inputs from federation
        self.charging_current = self.data_from_federation["inputs"]["charging_current"]

        # Update controller to regulate the charging current via the charging voltage
        if self.charging_current == 0: # EV no longer charging
            self.charging_current = 0  # Deactivate charger
        if self.charging_current < self.max_charging_current:
            if self.charging_voltage < self.max_charging_voltage:
                self.charging_voltage *= 1.02
            else:
                self.charging_voltage = self.max_charging_voltage
        else:
            if self.charging_voltage > self.min_charging_voltage:
                self.charging_voltage *= 0.98
            else:
                self.charging_voltage = self.min_charging_voltage
            
        # Send out new data to the federation
        self.data_to_federation["publications"]["charging_voltage"] = self.charging_voltage

if __name__ == "__main__":
    # Depending on command-line arguments this code can create either the EV
    # or the charger federate. 
    parser = argparse.ArgumentParser(description="Runs a federate for the EV charging example")
    parser.add_argument('-f', '--federate_type',
                        help="'EV' or 'charger'",
                        nargs='?',
                        default='EV')
    parser.add_argument('-is', '--initial_soc',
                        help="initial SOC of the EV battery, for EV ONLY",
                        nargs='?',
                        default=0.5)
    parser.add_argument('-iv', '--initial_voltage',
                        help="initial voltage of the charger, for charger ONLY",
                        nargs='?',
                        default=120)
    parser.add_argument('-s', '--scenario',
                        help="scenario name",
                        nargs='?',
                        default="scenario 1")
    args = parser.parse_args()

    if args.federate_type == 'EV':
        ev = CSTEV("ev") # federate name
        ev.soc = args.initial_soc
        ev.create_federate(args.scenario) #scenario name
        ev.run_cosim_loop()
        ev.destroy_federate()
    elif args.federate_type == 'charger':
        charger = CSTCharger("charger")
        charger.charging_voltage = args.initial_voltage
        charger.create_federate(args.scenario)
        charger.run_cosim_loop()
        charger.destroy_federate()
    else:
        raise ValueError(f"Invalid federate_type {args.federate_type}; expecting 'EV' or 'charger'")



