import sys
from cosim_toolbox.federate import Federate
import numpy as np
import logging
import json

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)


np.random.seed(2622)

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


class Battery(Federate):
    # def __init__(self, fed_name="Battery", schema="default", **kwargs):
    #     super().__init__(fed_name, **kwargs)
    #     scenario_name = kwargs.get("scenario_name", "HelicsExampleDefault")
    #     self.create_federate(scenario_name)
    
    def on_start(self) -> None:
        logger.debug("on_start")
        logger.debug(self.hfed.name)
        self.socs = np.array([0, 1])
        self.effective_R = np.array([8, 150])
        self.current_soc = {}
        # Data collection lists
        self.time_sim = []
        self.current = []
        self.soc = {}
        self.batt_list = get_new_battery(self.hfed.n_publications)
        for i in range(self.hfed.n_inputs):
            self.current_soc[i] = (np.random.randint(0,60))/100



    def update_internal_model(self) -> None:
        # Time request for the next physical interval to be simulated
        j = 0
        for input_name, input in self.inputs.items():
            ev_name = input_name.split("/")[1].split("_")[0]
            logger.debug(f'Battery {input_name} time {self.hfed.current_time}')

            # Get the applied charging voltage from the EV
            charging_voltage = self.data_from_federation["inputs"][input_name]
            logger.debug(f'\tReceived voltage {charging_voltage:.2f} from input'
                         f' {input_name}')

            # EV is fully charged and a new EV is moving in
            # This is indicated by the charging removing voltage when it
            #    thinks the EV is full
            if charging_voltage == 0:
                new_batt = get_new_battery(1)
                self.batt_list[j] = new_batt[0]
                self.current_soc[j] = (np.random.randint(0,80))/100
                charging_current = 0

            # Calculate charging current and update SOC
            R =  np.interp(self.current_soc[j], self.socs, self.effective_R)
            logger.debug(f'\tEffective R (ohms): {R:.2f}')
            charging_current = charging_voltage / R
            logger.debug(f'\tCharging current (A): {charging_current:.2f}')
            added_energy = (charging_current * charging_voltage * \
                           self.time_step/3600) / 1000
            logger.debug(f'\tAdded energy (kWh): {added_energy:.4f}')
            self.current_soc[j] = self.current_soc[j] + added_energy / self.batt_list[j]
            logger.debug(f'\tSOC: {self.current_soc[j]:.4f}')

            pub_key = f"Battery/{ev_name}_current"

            # Publish out charging current
            self.data_to_federation["publications"][pub_key] = charging_current
            logger.debug(f'\tPublished {pub_key} with value '
                         f'{charging_current:.2f}')

            # Store SOC for later analysis/graphing
            if input_name not in self.soc:
                self.soc[input_name] = []
            self.soc[input_name].append(float(self.current_soc[j]))
            
            j += 1

        # Data collection vectors
        self.time_sim.append(self.hfed.current_time)
        self.current.append(charging_current)
        logger.debug(json.dumps(self.data_to_federation, indent=4))

    def enter_executing_mode(self) -> None:
        """Moves the Federate to executing mode

        Similar to initializing mode, there are a few different ways of
        handling HELICS executing mode and what is implemented here is the
        simplest. If you need something more complex or specific, overload
        or redefine this method.
        """
        self.hfed.enter_executing_mode()
        self.on_start()

    def run(self, scenario_name: str) -> None:
        self.create_federate(scenario_name)
        self.run_cosim_loop()
        self.destroy_federate()

if __name__ == "__main__":
    
    _scenario_name = "HelicsExampleDefault"
    fed = Battery(fed_name="Battery")
    fed.run(_scenario_name)