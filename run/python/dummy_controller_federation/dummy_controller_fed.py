"""
Created on 3/11/2024

DummyControllerFederate class that defines the basic 
software interfaces for a controller for the ECOMP Offshore Wind (OSW) Usecase

@author: Shat Pratoomratana
shat.pratoomratana@pnnl.gov
"""

from cosim_toolbox.federate import Federate

def populate_bid(c0, c1, c2, Pmin, Pmax):
    
    bid = { "c2": c2,
            "c1": c1,
            "c0": c0,
            "Pmin": Pmin,
            "Pmax": Pmax
            }
    
    return bid


def create_day_ahead_energy_bid(current_time, wind_forecast_24_36hr, market_info):
    
    
    #do optimization  and generate coefficients. 
    c0 = 0
    c1 = 0
    c2 = 0
    Pmin = 0
    Pmax = 0
    
    bid = populate_bid(c0, c1, c2, Pmin, Pmax)
    
    return bid

def create_frequency_bid(current_time, wind_forecast_24_36hr, market_info):
    
    
    #do optimization and generate coefficients. 
    c0 = 0
    c1 = 0
    c2 = 0
    Pmin = 0
    Pmax = 0
    
    bid = populate_bid(c0, c1, c2, Pmin, Pmax)
    
    return bid
    
def create_real_time_energy_bid(current_time, wind_speed_current_period, market_info):
    
    
    #do optimization and generate coefficients. 
    c0 = 0
    c1 = 0
    c2 = 0
    Pmin = 0
    Pmax = 0
    
    bid = populate_bid(c0, c1, c2, Pmin, Pmax)
    
    return bid

def create_dispatch(current_time):
#Transmit dispatch signals to the Grid + Market federate. 
#The model of the physical grid state is maintained by the Grid + Market federate. 
#For the T2 Entity to impact the operation of the power system it must communicate its 
#state to the Grid + Market federate so that the grid model can be updated. 

    dispatch = {
    "P":
        [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    "Q": 
        [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
                }

    return dispatch
    

def update_OSW_ES_model_state(current_time, wind_speed_current_period):
#One specific function not previously mentioned is not a part of the market interaction: 
#updating the OSW + energy storage model state. This function is generally outside the market 
#interactions as it is intended to allow the model to update its current state at a frequency
# that is appropriate for the proper modeling of the system. 
    new_time = current_time
    new_wind_speed = wind_speed_current_period


def init_windfarm(): 
    capacity = 0
    battery_size = 0
    on_off_shore_battery = True
    droop_parameters = 0
    turbine_parameters = 0
    number_of_turbines = 0


def day_ahead_clearing_results(current_time, day_ahead_clearing, reserve_clearing):
    #not sure about this one
    placeholder = 0


class DummyControllerFederate(Federate):
    
    def __init__(self, fed_name="", schema="default", **kwargs):
        super().__init__(fed_name, **kwargs)
        
    

    def update_internal_model(self):
        """
        This is entirely user-defined code and is intended to be defined by
        sub-classing and overloading.
        """
        if not self.debug:
            raise NotImplementedError("Subclass from Federate and write code to update internal model")
        
        #keys for publications
        DAM_pub_key = "Controller/DAM_bid"
        freq_pub_key = "Controller/frequency_bid"
        realtime_pub_key = "Controller/realtime_bid"
        #keys for the subscriptions
        DAM_sub_key = "Market/DAM_clearing_info"
        freq_sub_key = "Market/frequency_clearing_info"
        realtime_sub_key = "Market/realtime_clearing_info"
    
        #get market clearing info from the market federate via HELICS
        DAM_clearing_info = self.data_from_federation["inputs"][DAM_sub_key]
        freq_clearing_info = self.data_from_federation["inputs"][freq_sub_key]
        realtime_clearing_info = self.data_from_federation["inputs"][realtime_sub_key]

        wind_speed = 0 #get from helics?
        wind_forecast = 0 #get from helics?
        current_time = self.granted_time

        #use market clearing information to create bids then send them out via HELICS
        self.data_to_federation["publication"][DAM_pub_key] = create_day_ahead_energy_bid(current_time,wind_forecast,DAM_clearing_info)
        self.data_to_federation["publication"][freq_pub_key] = create_frequency_bid(current_time,wind_forecast,freq_clearing_info)
        self.data_to_federation["publication"][realtime_pub_key] = create_real_time_energy_bid(current_time,wind_speed,realtime_clearing_info)

    
        return super().update_internal_model()   
    
        
if __name__ == "__main__":
    test_fed = DummyControllerFederate("Controller")    
    test_fed.create_federate("dummy_controller_federate")
    test_fed.run_cosim_loop()
    test_fed.destroy_federate()    