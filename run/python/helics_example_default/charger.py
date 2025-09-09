import argparse
from cosim_toolbox.federate import Federate
import helics as h
import logging
import numpy as np
import json

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

np.random.seed(268)

def calc_charging_voltage(EV_list):
    """
    This function uses the pre-defined charging powers and maps them to
    standard (more or less) charging voltages. This allows the charger
    to apply an appropriately modeled voltage to the EV based on the
    charging power level

    :param EV_list: Value of "1", "2", or "3" to indicate charging level
    :return: charging_voltage: List of charging voltages corresponding
            to the charging power.
    """

    charging_voltage = []
    # Ignoring the difference between AC and DC voltages for this application
    charge_voltages = [120, 240, 630]
    for EV in EV_list:
        if EV == 1:
            charging_voltage.append(charge_voltages[0])
        elif EV == 2:
            charging_voltage.append(charge_voltages[1])
        elif EV == 3:
            charging_voltage.append(charge_voltages[2])
        else:
            charging_voltage.append(0)

    return charging_voltage


def get_new_EV(numEVs):
    """
    Using hard-coded probabilities, a distribution of EVs with support
    for specific charging levels are generated. The number of EVs
    generated is defined by the user.

    :param numEVs: Number of EVs
    :return
        numLvL1: Number of new EVs that will charge at level 1
        numLvL2: Number of new EVs that will charge at level 2
        numLvL3: Number of new EVs that will charge at level 3
        listOfEVs: List of all EVs (and their charging levels) generated

    """

    # Probabilities of a new EV charging at the specified level.
    lvl1 = 0.05
    lvl2 = 0.6
    lvl3 = 0.35
    listOfEVs = np.random.choice([1, 2, 3], numEVs, p=[lvl1, lvl2, lvl3]).tolist()
    numLvl1 = listOfEVs.count(1)
    numLvl2 = listOfEVs.count(2)
    numLvl3 = listOfEVs.count(3)

    return numLvl1, numLvl2, numLvl3, listOfEVs



def get_new_battery(numBattery):
    '''
    Using hard-coded probabilities, a distribution of battery of
    fixed battery sizes are generated. The number of batteries is a user
    provided parameter.

    :param numBattery: Number of batteries to generate
    :return
        listOfBatts: List of generated batteries

    '''

    # Probabilities of a new EV having a battery at a given capacity.
    #   The three random values (25,62, 100) are the kWh of the randomly
    #   selected battery.
    size_1 = 0.2
    size_2 = 0.2
    size_3 = 0.6
    listOfBatts = np.random.choice([25,62,100],numBattery,p=[size_1,size_2,
                                                       size_3]).tolist()

    return listOfBatts


class Charger(Federate):
    # def __init__(self, fed_name="Charger", analysis="default", **kwargs):
    #     super().__init__(fed_name, **kwargs)
    #     scenario_name = kwargs.get("scenario_name", "HelicsExampleDefault")
    #     print(f"scenario_name={scenario_name}")
    #     self.create_federate(scenario_name)
    #     print("Scenario:")
    #     print(self.scenario)
    #     print("config")
    #     print(self.config)
    
    def on_start(self) -> None:
        logger.debug("~~~~~~~~~~~~ on_start ~~~~~~~~~~~~")
        logger.debug(self.hfed.name)
        # Definition of charging power level (in kW) for level 1, 2, 3 chargers
        self.charge_rate = [1.8, 7.2, 50]

        # Generate an initial fleet of EVs, one for each previously defined
        #   handle. This gives each EV a unique link to the EV controller
        #   federate.
        self.numLvl1, self.numLvl2, self.numLvl3, self.EVlist = get_new_EV(self.hfed.n_publications)
        self.charging_voltage = calc_charging_voltage(self.EVlist)
        self.currentsoc = {}

        # Data collection lists
        self.time_sim = []
        self.power = []
        self.charging_current = {}

    def on_enter_executing_mode(self):
        # pass
        for j, pub_key in zip(range(self.hfed.n_publications), self.pubs.keys()):
            self.hfed.publications[pub_key].publish(self.charging_voltage[j])
            # h.helicsPublicationPublishDouble(pubid[j], charging_voltage[j])
            logger.debug(
                f"\tPublishing {pub_key} of {self.charging_voltage[j]}"
                f" at time {self.current_time}"
            )

    def update_internal_model(self) -> None:
        logger.debug("~~~~~~~~~~~~ update_internal_model ~~~~~~~~~~~~")
        # Time request for the next physical interval to be simulated
        logger.debug("data_from_federation")
        logger.debug(json.dumps(self.data_from_federation, indent=4))
        j = 0
        for input_name, input in self.inputs.items():
            ev_name = input_name.split("/")[1].split("_")[0]
            logger.debug(f"{ev_name} time {self.hfed.current_time}")
            # Model the physics of the battery charging. This happens
            #   every time step whether a message comes in or not and always
            #   uses the latest value provided by the battery model.
            self.charging_current[j] = self.data_from_federation["inputs"][input_name]
            logger.debug(
                f"\tCharging current: {self.charging_current[j]:.2f} from"
                f" input {input_name}"
            )

            # Publish updated charging voltage
            pub_key = f"Charger/{ev_name}_voltage"
            self.data_to_federation["publications"][pub_key] = self.charging_voltage[j]
            logger.debug(
                f"\tPublishing {pub_key} of {self.charging_voltage[j]}"
                f" at time {self.hfed.current_time}"
            )
            j = j + 1

        # Calculate the total power required by all chargers. This is the
        #   primary metric of interest, to understand the power profile
        #   and capacity requirements required for this charging garage.
        total_power = 0
        for j in range(self.hfed.n_inputs):
            if self.charging_current[j] > 0:  # EV is still charging
                total_power += self.charging_voltage[j] * self.charging_current[j]

        # Data collection vectors
        self.time_sim.append(self.hfed.current_time)
        self.power.append(total_power)
        logger.debug("~~~~~~~~~~~~ data_to_federation ~~~~~~~~~~~~")
        logger.debug(json.dumps(self.data_to_federation, indent=4))


    def run(self, scenario_name: str) -> None:
        self.create_federate(scenario_name)
        self.run_cosim_loop()
        self.destroy_federate()

if __name__ == "__main__":
    _scenario_name = "HelicsExampleDefault"
    fed = Charger(fed_name="Charger")
    fed.run(_scenario_name)