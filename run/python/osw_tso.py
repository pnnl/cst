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
import os
import sys

FILEDIR, tail = os.path.split(__file__)
RUNDIR, tail = os.path.split(FILEDIR)
CUDIR, tail = os.path.split(RUNDIR)
cosim_toolbox_pth = os.path.join(CUDIR, "src", "cosim_toolbox")
sys.path.append(cosim_toolbox_pth)

# internal packages
from egret.data.model_data import ModelData
from egret.models.unit_commitment import solve_unit_commitment, SlackType
import pyenergymarket as pyen

from cosim_toolbox.federate import Federate
from osw_da_market import OSWDAMarket
from osw_rt_market import OSWRTMarket
# from osw_reserves_market import OSWReservesMarket

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.ERROR)

class OSWTSO(Federate):
    """
    TSO-like object used in E-COMP off-shore wind use case. This is way more
    particular to that analysis than I'd like but in the name of expediency,
    this is where I landed.

    Implements three markets:
            - Day-ahead energy markets
            - Frequency regulation market (implement as a reserve market)
            - Real-time energy market.

    The market operations are handled by EGRET, the management of time
    and the HELICS integration is handled here by the Federate class from
    which we are inheriting. 

    This code adds the instantiation of the market objects and the 
    underlying state machine that defines when particular activity
    takes place. A lot of that timing is defined in the market_timing
    object (well, dictionary as I write it now; it should be an 
    instance of a class, I think, but I'm running out of time). The
    data there defines the progression of the market state machine and the
    associated timing.
    
    This class assummes that the EGRET functionality is presented in a
    class- or library-oriented method such that the market operation 
    methods can be called as stand-alone operations. 
    """

    def __init__(self, fed_name, market_timing, **kwargs):
        """
        Add a few extra things on top of the Federate class init

        For this to work using kwargs, the names of the parameter values have
        to match those expected by this class. Those parameter names are shown
        below and all are floats with the units of seconds.
        
        """
        super().__init__(fed_name)

        # This translates all the kwarg key-value pairs into class attributes
        self.__dict__.update(kwargs)

        # Holds the market objects 
        self.markets = {}

        self.markets["da_energy_market"] = OSWDAMarket("da_energy_market", market_timing["da"])
        # self.markets["reserves_market"] = OSWReservesMarket("reserves_market", market_timing["reserves"])
        self.markets["rt_energy_market"] = OSWRTMarket("rt_energy_market", market_timing["rt"])

        # I don't think we will ever use the "last_market_time" values 
        # but they will give us confidence that we're doing things correctly.

        self.market_timing = market_timing
        self.markets = self.calculate_initial_market_times(self.markets)
    

    def calculate_initial_market_times(self, markets):
        """
        Calculates the initial .next_state_time for each of the markets in the
        provided dictionary of market objects. (They're not really objects but
        whatever.)
        """
        for market_name, market in markets.items():
            last_state_time, next_state_time = self.markets[market_name].calculate_next_state_time(market.market_timing,
                                                                                market.current_state,
                                                                                market.next_state_time)
            markets[market_name].last_state_time = last_state_time
            markets[market_name].next_state_time = next_state_time
        return markets

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
        self.gv = pyen.GVParse(self.h5path, default=default, logger_options={"level": self.loglevel})

    def initialze_power_and_market_model(self):
        """
        Initializes the power system and market models

        This should probably return something, even if its self.something
        """
        ## Create an Egret "ModelData" object, which is just a lightweight
        ## wrapper around a python dictionary, from an Egret json test instance
        self.md = ModelData(self.gv)


    def calculate_next_requested_time(self):
        """
        Overload of Federate class method

        When update_internal_model is run, it calls update_market on the
        market object which calculates the next state time (next market
        state). To calculate the next time request, we just need the 
        minimum of these saved market states.
        """

        self.next_requested_time = min(self.markets["da_energy_market"].next_state_time, 
                                       self.markets["rt_energy_market"].next_state_time)
        return self.next_requested_time


    def update_power_system_and_market_state(self):
        """
        Reads in time-series values and values received via HELICS and applies
        them appropriately to the power system model. May involve reading 
        "self.data_from_federation"
        """
        ## solve the unit commitment instance using solver (gurobi or cbc)
        self.md_sol = solve_unit_commitment(self.md, self.solver, slack_type=SlackType.TRANSMISSION_LIMITS,
                                    mipgap=0.01,
                                    timelimit=300, solver_tee=True)

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
        # TODO: may need to process results prior to returning them
        self.markets["da_energy_market"].update_market()
        return self.markets["da_energy_market"].market_results
        

    def run_reserve_market(self):
        """
        Using EGRET, clears the reserve market in the form of a unit
        committment optimization problem.

        TDH hopes this will be straight-forward and may take the form of calls
        to methods of an EGRET object.
        """

        # TODO: may need to process results prior to returning them
        self.markets["reserve_market"].run_market()
        return self.markets["reserve_market"].market_results
       

    def run_rt_ed_market(self):
        """
        Using EGRET, clears the RT energy market in the form of an
        economic dispatch optimization problem.

        TDH hopes this will be straight-forward and may take the form of calls
        to methods of an EGRET object.
        """

        # TODO: may need to process results prior to returning them
        self.markets["rt_energy_market"].run_market()
        return self.markets["rt_energy_market"].market_results

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

        if self.markets["da_energy_market"]["next_state_time"] == self.granted_time:
            self.generate_wind_forecasts()
            da_results = self.run_da_uc_market()
            reserve_results = self.run_reserve_market()
            self.data_to_federation["publication"]["da_clearing_result"] = da_results["prices"]["osw_node"]
            self.data_to_federation["publication"]["reserve_clearing_result"] = reserve_results["prices"]["osw_node"]
        if self.market_times["RT"]["next_market_time"] == self.granted_time:
            rt_results = self.run_rt_ed_market()
            self.data_to_federation["publication"]["rt_clearing_result"] = rt_results["prices"]["osw_node"]
        
if __name__ == "__main__":
    # TODO: we might need to make this an actual object rather than a dict.
    # Even now, I see it starting to get messy.

    # The "initial_offset" value is used to indicate to the object that the 
    # market cycle is not beginning precisely at the beginning of "idle".
    # Similarly, an "initial state" needs to be defined as well.
    # This value is in the same units as the other values in the dictionary.

    # 15-minute market with bidding beginning five minutes before the end of 
    # the market interval and ending when clearing begins two minutes before 
    # the end of the interval.
    rt_market_timing = {
            "states": {
                "idle": {
                    "start_time": 0,
                    "duration": 600
                },
                "bidding": {
                    "start_time": 600,
                    "duration": 180
                },
                "clearing": {
                    "start_time": 780,
                    "duration": 120
                }
            },
            "initial_offset": 0,
            "initial_state": "idle",
            "market_interval": 900
        }
    # Daily market with bidding beginning nine minutes before the end of 
    # the market interval and ending when clearing begins one minutee before 
    # the end of the interval.
    da_market_timing = {
            "states": {
                "idle": {
                    "start_time": 0,
                    "duration": 85500
                },
                "bidding": {
                    "start_time": 85800,
                    "duration": 540
                },
                "clearing": {
                    "start_time": 86340,
                    "duration": 60
                },
            },
            "initial_offset": 0,
            "initial_state": "idle",
            "market_interval": 86400
        }
    market_timing = {"da": da_market_timing, 
                      "reserves": da_market_timing,
                      "rt": rt_market_timing}
    
    h5filepath = "C:\\Users\\kell175\\pyenergymarket\\data_model_tests\\data_files\\WECC240_20240807.h5"
    default = {
        "time": {
            "datefrom": "2032-02-01"
        },
        "simulation": {
            "thermal_model": "cost", # this is the default
        },
        "elements": {
            "branch":{
                "rating_long_term": "A",
                "rating_short_term": "A",
                "rating_emergency": "B"
            },
            "generator": {
                "generator_type_map":{
                    "storage": [3, 10]
                },
                "renewable_type_override": {3: "Solar"},
                "ignore_non_fuel_startup": False,
                "scale_fuel_cost": 1.0
            }
        }
    }
    loglevel = "INFO"
    solver = "cbc"

    wecc_market_fed = OSWTSO("WECC_market", market_timing, h5file=h5filepath, default=default, loglevel=loglevel, solver=solver)
    wecc_market_fed.create_federate("wecc_market")
    wecc_market_fed.run_cosim_loop()
    wecc_market_fed.destroy_federate()