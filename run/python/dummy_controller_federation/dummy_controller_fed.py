"""
Created on 3/11/2024

DummyControllerFederate class that defines the basic 
software interfaces for a controller for the ECOMP Offshore Wind (OSW) Usecase

@author: Shat Pratoomratana
shat.pratoomratana@pnnl.gov
"""

from cosim_toolbox.federate import Federate


class DummyControllerFederate(Federate):
    
    def __init__(self, fed_name="", schema="default", **kwargs):
        super().__init__(fed_name, **kwargs)
    # TDH: Add class attributes/parameters here. See federate.py for example

    # TDH: Add type hinting to all class methods. See federate.py for example.
    def populate_bid(self, c0, c1, c2, Pmin, Pmax):
        """
        Takes input parameters and puts them into the bid dictionary and
        returns it.
        """
        bid = { "c2": c2,
                "c1": c1,
                "c0": c0,
                "Pmin": Pmin,
                "Pmax": Pmax
                }
        return bid


    def create_day_ahead_energy_bid(self, current_time, wind_forecast_24_36hr, market_info):
        """
        Creates the day-ahead energy bid based on the provided forecasts and returns
        the bid data dictionary.
        """
        
        #do optimization  and generate coefficients. 
        c0 = 0
        c1 = 0
        c2 = 0
        Pmin = 0
        Pmax = 0
        
        bid = self.populate_bid(c0, c1, c2, Pmin, Pmax)
        
        return bid


    def create_frequency_bid(self, current_time, wind_forecast_24_36hr, market_info):
        """
        Creates the frequency bid based on the provided forecasts and returns
        the bid data dictionary.
        """
        #do optimization and generate coefficients. 
        c0 = 0
        c1 = 0
        c2 = 0
        Pmin = 0
        Pmax = 0
        
        bid = self.populate_bid(self, c0, c1, c2, Pmin, Pmax)
        
        return bid


    def create_real_time_energy_bid(self, current_time, wind_speed_current_period, market_info):
        """
        Creates the real-time energy bid based on current power system state and 
        returns the bid data dictionary.
        """
        
        #do optimization and generate coefficients. 
        c0 = 0
        c1 = 0
        c2 = 0
        Pmin = 0
        Pmax = 0
        
        bid = self.populate_bid(c0, c1, c2, Pmin, Pmax)
        
        return bid


    def create_dispatch(self, current_time):
        """
        Transmit dispatch signals to the Grid + Market federate. The model of the
        physical grid state is maintained by the Grid + Market federate. For the 
        T2 Entity to impact the operation of the power system it must communicate its 
        state to the Grid + Market federate so that the grid model can be updated.
        """
    

        dispatch = {
        "P":
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
        "Q": 
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
                    }

        return dispatch


    def update_OSW_ES_model_state(self, current_time, wind_speed_current_period):
        """
        One specific function not previously mentioned is not a part of the market
        interaction: updating the OSW + energy storage model state. This function
        is generally outside the market interactions as it is intended to allow the
        model to update its current state at a frequency that is appropriate for 
        the proper modeling of the system. 
        """

        new_time = current_time
        new_wind_speed = wind_speed_current_period

    def get_wind_forecast(self, current_time, num_hours) -> list:
        """
        Pulls in the wind forecast and returns it.

        At this time, the source of the wind forecast is undefined. That is,
        we don't know if the forecast is a file we read in or a database 
        query.

        Trevor's preference is that we load the data into the time-series
        database during co-sim set-up and read it in here using the CST
        API for accessing such data.
        """
        dummy_forecast = []
        for hour in range(num_hours):
            dummy_forecast.append(100 + hour)

        return dummy_forecast
    

    def get_windspeed(self) -> float:
        """
        Pulls the current windspeed and returns it

        At this time, the source of the wind data is undefined. That is,
        we don't know if the data is a file we read in or a database 
        query.

        Trevor's preference is that we load the data into the time-series
        database during co-sim set-up and read it in here using the CST
        API for accessing such data.
        """
        dummy_windspeed = 10

        return dummy_windspeed


    def gather_day_ahead_clearing_results(self, current_time, day_ahead_clearing, reserve_clearing):
        #not sure about this one
        placeholder = 0

    def init_windfarm(self): 
        # TDH: Create these as attributes of the class defined in the
        #   "__init__()" method.
        capacity = 0
        battery_size = 0
        on_off_shore_battery = True
        droop_parameters = 0
        turbine_parameters = 0
        number_of_turbines = 0

    def update_internal_model(self):
        """
        Controls the operation of the off-shore wind farm into the wholesale
        market. Calls methods defined by T2 to create the bids for market
        participation.
        """
        if not self.debug:
            raise NotImplementedError("Subclass from Federate and write code to update internal model")
        
        #keys for publications
        # TDH: Move to "__init__()" of this class 
        DAM_pub_key = "Controller/DAM_bid"
        freq_pub_key = "Controller/frequency_bid"
        realtime_pub_key = "Controller/realtime_bid"
        #keys for the subscriptions
        DAM_sub_key = "Market/DAM_clearing_info"
        freq_sub_key = "Market/frequency_clearing_info"
        realtime_sub_key = "Market/realtime_clearing_info"

        # TDH: I'm not seeing "market_info" called out in the function
        #   definition. Do we know how it is defined? Should it be an 
        #   attribute of this federate?
        market_info = {}
    
        # TDH: This should only happen at certain timesteps in the simulation 
        #   We can add a custom field in the configuration of this federate  
        #   that defines at what simulation times these functions need to run
        #   For example, we may define the day-ahead bids need to be created 
        #   at 10am each day or the real-time bids need to be created every
        #   15 minutes. We can discuss more when you get a chance to look 
        #   at this again.
        #get market clearing info from the market federate via HELICS
        DAM_clearing_info = self.data_from_federation["inputs"][DAM_sub_key]
        freq_clearing_info = self.data_from_federation["inputs"][freq_sub_key]
        realtime_clearing_info = self.data_from_federation["inputs"][realtime_sub_key]
        wind_forecast = self.get_wind_forecast(self.granted_time, 24)
        DAM_bid = self.create_day_ahead_energy_bid(self.granted_time, wind_forecast, market_info)
        frequency_bid = self.create_frequency_bid(self.granted_time, wind_forecast, market_info)

        windspeed = self.get_windspeed()
        RTM_bid = self.create_real_time_energy_bid(self.granted_time, windspeed, market_info)
        dispatch = self.create_dispatch(self.granted_time)

        # TDH: See above comment on when the bids need to be created. Similarly,
        #   the results only need to be published on a simliar schedule.
        #use market clearing information to create bids then send them out via HELICS
        self.data_to_federation["publication"][DAM_pub_key] = DAM_bid
        self.data_to_federation["publication"][freq_pub_key] = frequency_bid
        self.data_to_federation["publication"][realtime_pub_key] = RTM_bid

    
        return super().update_internal_model()   
    
        
if __name__ == "__main__":
    test_fed = DummyControllerFederate("Controller")    
    test_fed.create_federate("dummy_controller_federate")
    test_fed.run_cosim_loop()
    test_fed.destroy_federate()    