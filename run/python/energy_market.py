"""
Created on 06/25/2024

Class for the new PyEnergyMarket simulator that wraps EGRET

This assumes EGRET functionality has been implemented as class functions that 
can be called as methods. (This may not be a hard assumption.)


@author: Trevor Hardy
trevor.hardy@pnnl.gov
"""
import datetime
import json
import logging

import helics as h

import cosim_toolbox.metadataDB as mDB

# Assumes these libraries have classes that exist with the appropriate method
# names
import egret

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.ERROR)

class EnergyMarket(federate):
    """
    Implements three markets for use in the E-COMP off-shore wind use case:
            - Day-ahead energy markets
            - Frequency regulation market (implement as a reserve market)
            - Real-time energy market.

    The market operations are handled by EGRET, the management of time
    and the HELICS integration is handled here by the Federate class from
    which we are inheriting.
    
    This class assummes that the EGRET functionality is presented in a
    class- or library-oriented method such that the market operation 
    methods can be called as stand-alone operations. 
    """

    def __init__(self, fed_name="", **kwargs):
        """
        Add a few extra things on top of the Federate class init

        For this to work using kwargs, the names of the parameter values have
        to match those expected by this class. Those parameter names are shown
        below and all are floats with the units of seconds.

        da_market_interval - How often the DA market occurs in seconds
        
        da_market_first_time - When, relative to the first simulated time, 
        the first DA market bids must be submitted. This is the same interval
        used for the reserves market

        rt_market_interval - How often the RT market occurs in seconds

        rt_market_first_time - When, relative to the first simulated time, 
        the first RT market bids must be submitted. This is the same interval
        used for the reserves market
        
        """
        super.__init__(self, fed_name)

        # This translates all the kwarg key-value pairs into class attributes
        self.__dict__.update(kwargs)

        # Holds the market objects instantiated by EGRET
        self.markets = {}

        self.markets["da_energy_market"] = egret.create_uc_market()
        self.markets["reserves_market"] = egret.create_uc_market()
        self.markets["rt_energy_market"] = egret.create_ed_market()

        # I don't think we will ever use the "last_market_time" values 
        # but they will give us confidence that we're doing things correctly.
        self.market_times = {
            "DA": {
                "last_market_time": 0,
                "next_market_time": -1
            },
            "RT": {
                "last_market_time": 0,
                "next_market_time": -1
            }
        }
        self.market_times = self.calculate_initial_market_times()

    def calculate_initial_market_times(self):
        """
        Since the first time either the DA or RT energy markets need to run
        depends on the starting simulation time, the "next_market_time" values
        for the very first market are a special snowflake calculation.
        """
        return self.market_times
    
    def enter_initialization(self):
        """
        Overload of Federate class method

        Prior to entering the HELICS initialization mode, we need to read
        in the model and do some initialization on everything
        """

        self.read_power_system_model()
        self.initialze_power_and_market_model()

        self.hfed.enter_initializing_mode() # HELICS API call

    def read_power_system_model(self):
        """
        Reads in the power system model into the native EGRET format.

        This should probably return something, even if its self.something
        """
        pass

    def initialze_power_and_market_model(self):
        """
        Initializes the power system and market models

        This should probably return something, even if its self.something
        """
        pass


    def calculate_next_requested_time(self):
        """
        Overload of Federate class method

        Based on the current granted time and the market intervals, the next 
        requested time needs to be calculated. This method calculates the 
        next time to be requested (self.next_requested_time, used by the 
        Federate class) as well as indicate in self.market_times what 
        market(s) will be run at that time.

        This doesn't handle defining the simulation times when the markets 
        will initally run; that is handled in the class init method.
        """
        if self.market_times["DA"]["next_market_time"] == self.granted_time:
            self.market_times["DA"]["last_market_time"] = self.granted_time
            self.market_times["DA"]["next_market_time"] = self.granted_time + self.da_market_interval
        if self.market_times["RT"]["next_market_time"] == self.granted_time:
            self.market_times["RT"]["last_market_time"] = self.granted_time
            self.market_times["RT"]["next_market_time"] = self.granted_time + self.rt_market_interval

        self.next_requested_time = min(self.market_times["DA"]["next_market_time"], 
                                       self.market_times["RT"]["next_market_time"])
        return self.next_requested_time


    def update_power_system_and_market_state(self):
        """
        Reads in time-series values and values received via HELICS and applies
        them appropriately to the power system model. May involve reading 
        "self.data_from_federation"
        """
        pass

    def generate_wind_forecasts(self) -> list:
        """
        The T2 controller needs 30 wind forecast profiles to run their 
        optimization thus we generate them
        """
        forecast_list = []
        return forecast_list

    def run_da_uc_market(self):
        """
        Using EGRET, clears the DA energy market in the form of a unit
        committment optimization problem.

        TDH hopes this will be straight-forward and may take the form of calls
        to methods of an EGRET object.
        """
        # TODO: update this call with the actual method name and signature
        # TODO: may need to process results prior to returning them
        return self.markets["da_energy_market"].run_market()
        

    def run_reserve_market(self):
        """
        Using EGRET, clears the reserve market in the form of a unit
        committment optimization problem.

        TDH hopes this will be straight-forward and may take the form of calls
        to methods of an EGRET object.
        """

        # TODO: update this call with the actual method name and signature
        # TODO: may need to process results prior to returning them
        return self.markets["reserve_market"].run_market()
       

    def run_rt_ed_market(self):
        """
        Using EGRET, clears the RT energy market in the form of an
        economic dispatch optimization problem.

        TDH hopes this will be straight-forward and may take the form of calls
        to methods of an EGRET object.
        """

        # TODO: update this call with the actual method name and signature
        # TODO: may need to process results prior to returning them
        return self.markets["rt_energy_market"].run_market()

    def update_internal_model(self):
        """
        Overload of Federate class method

        For interactions with the rest of the federation, see the 
        inline comments from the "get_data_from_federate" and 
        "send_data_to_federation" methods. These  methods use 
        "self.data_from_federation" and "self.data_to_federation"
        data structures. Those attributes will be utilized inside this method
        to access the data coming from or going to the federation (but
        without having to know the HELICS APIs).

        This is the method where the market will run, getting bids from the
        market participant, clearing the market, and sending out the market
        clearing signals.

        "calculate_next_time_step" has populated "self.market_times" to
        indicate which markets need to be run
        """
        self.update_power_system_and_market_state()

        if self.market_times["DA"]["next_market_time"] == self.granted_time:
            self.generate_wind_forecasts()
            da_results = self.run_da_uc_market()
            reserve_results = self.run_reserve_market()
            self.data_to_federation["publication"]["da_clearing_result"] = da_results["prices"]["osw_node"]
            self.data_to_federation["publication"]["reserve_clearing_result"] = reserve_results["prices"]["osw_node"]
        if self.market_times["RT"]["next_market_time"] == self.granted_time:
            rt_results = self.run_rt_ed_market()
            self.data_to_federation["publication"]["rt_clearing_result"] = da_results["prices"]["osw_node"]
        
if __name__ == "__main__":
    wecc_market_fed = EnergyMarket("WECC_market")
    wecc_market_fed.create_federate("wecc_market")
    wecc_market_fed.run_cosim_loop()
    wecc_market_fed.destroy_federate()