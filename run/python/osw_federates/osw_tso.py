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
import pandas as pd

# internal packages
import pyenergymarket as pyen

from cosim_toolbox.federate import Federate
from cosim_toolbox.dataLogger import DataLogger
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

    def __init__(self, fed_name, market_timing, markets:dict={}, **kwargs):
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
        self.markets = markets

        # I don't think we will ever use the "last_market_time" values 
        # but they will give us confidence that we're doing things correctly.

        # Set up the timeseries database
        # self.dl = DataLogger()
        # self.dl.open_database_connections()
        # self.dl.check_version()
        # if self.dl.table_exist(self.scenario['osw_test_schema'], "htd_double"):
        #     self.dl.create_schema(self.scenario['osw_test_schema'])
        #     self.dl.make_logger_database(self.scenario['osw_test_schema']) 

        self.market_timing = market_timing
        self.markets = self.calculate_initial_market_times(self.markets)

        # self.dl = DataLogger()
        # self.dl.open_database_connections()
        # self.dl.check_version()
        # print(self.scenario)
        # if self.dl.table_exist(self.scenario['osw_test_schema'], "htd_double"):
        #     self.dl.create_schema(self.scenario['osw_test_schema'])
        #     self.dl.make_logger_database(self.scenario['osw_test_schema'])
        #     self.dl.data_db.commit()

    def calculate_initial_market_times(self, markets):
        """
        Calculates the initial .next_state_time for each of the markets in the
        provided dictionary of market objects. (They're not really objects but
        whatever.)
        """
        for market_name, market in markets.items():
            last_state_time, next_state_time = self.markets[market_name].calculate_next_state_time()
            markets[market_name].last_state_time = last_state_time
            markets[market_name].next_state_time = next_state_time
            print(market_name, last_state_time, next_state_time)
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
        ## Create an Egret "ModelData" object, which is just a lightweight
        ## wrapper around a python dictionary, from an Egret json test instance
        pass # right now this is done outside the class.
        

    def initialze_power_and_market_model(self):
        """
        Initializes the power system and market models

        This should probably return something, even if its self.something
        """
        # Should get an initial run of the DAM with a longer window and
        # throw away the first couple days
        pass


    def calculate_next_requested_time(self):
        """
        Overload of Federate class method
 
        When update_internal_model is run, it calls update_market on the
        market object which calculates the next state time (next market
        state). To calculate the next time request, we just need the
        minimum of these saved market states.
        """
        dam_lt, dam_nt = self.markets["da_energy_market"].calculate_next_state_time()
        rtm_lt, rtm_nt = self.markets["rt_energy_market"].calculate_next_state_time()
        self.next_requested_time = min(self.markets["da_energy_market"].next_state_time, self.markets["rt_energy_market"].next_state_time)
        print("DAM", dam_lt, "DAM_Nt: ", dam_nt)
        print("RTM", rtm_lt, "RTM_Nt: ", rtm_nt)
        print("Requested time: ", self.next_requested_time)
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
        # TODO: may need to process results prior to returning them
        current_state_time = self.markets["da_energy_market"].update_market()
        self.markets["da_energy_market"].move_to_next_state()
        if self.markets["da_energy_market"].state == "clearing":
            return self.markets["da_energy_market"].market_results
        else:
            return current_state_time
        

    def run_reserve_market(self):
        """
        NOTE: Currently this is being run in the day ahead market.
        Using EGRET, clears the reserve market in the form of a unit
        committment optimization problem.

        TDH hopes this will be straight-forward and may take the form of calls
        to methods of an EGRET object.
        """

        # TODO: may need to process results prior to returning them
        self.markets["reserve_market"].update_market()
        return self.markets["reserve_market"].market_results
       

    def run_rt_ed_market(self):
        """
        Using EGRET, clears the RT energy market in the form of an
        economic dispatch optimization problem.

        TDH hopes this will be straight-forward and may take the form of calls
        to methods of an EGRET object.
        """
        print("I MADE IT INTO RTM")
        # TODO: may need to process results prior to returning them
        current_state_time = self.markets["rt_energy_market"].update_market()
        self.markets["rt_energy_market"].move_to_next_state()
        if self.markets["rt_energy_market"].state == "clearing":
            return self.markets["rt_energy_market"].market_results
        elif self.markets["rt_energy_market"].state == "bidding":
            # TODO put commitment from dam into rtm
            pass
        else:
            return current_state_time

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

        if self.markets["da_energy_market"].next_state_time == round(self.granted_time):
            if self.markets["da_energy_market"].state == "idle":
                self.generate_wind_forecasts() # TODO Publish these for T2 (OSW_Plant) federate to subscribe to
            da_results = self.run_da_uc_market()
            
            #reserve_results = self.run_reserve_market()
            #self.data_to_federation["publication"]["da_clearing_result"] = da_results["prices"]["osw_node"]
            if self.markets["da_energy_market"].state == "clearing":
                print("da_results:", da_results.data["system"])
                area_keys = ['CALIFORN', 'MEXICO', 'NORTH', 'SOUTH']
                price_keys = ['regulation_up_price', 'regulation_down_price', 'flexible_ramp_up_price', 'flexible_ramp_down_price']
                price_dict = {}
                for bus, b_dict in da_results.elements(element_type="bus"):
                    b_dict["lmp"]
                for area, area_dict in da_results.elements(element_type="area"):
                    for key in price_keys:
                        price_dict[area+' '+key] = da_results.data["elements"]["area"][area][key]
                print("price results:", price_dict)
            else:
                print("da_next_time:", da_results)
            #self.data_to_federation["publication"]["reserve_clearing_result"] = da_results["reserves_prices"]["osw_area"]
        if self.markets["rt_energy_market"].next_state_time == round(self.granted_time):
            rt_results = self.run_rt_ed_market()
            #self.data_to_federation["publication"]["rt_clearing_result"] = rt_results["prices"]["osw_node"]
        else:
            print(self.markets["rt_energy_market"].next_state_time, type(self.markets["rt_energy_market"].next_state_time), self.granted_time, type(self.granted_time))

    def run_market_loop(self, market, file_name):
        """ 
        This method will run through a single market loop when HELICS isn't being used to advance time. 
        Used for testing or an easy way to generate LMPs without feedbacks.
        """

        start_times = self.markets[market].start_times
        for t in start_times:
            da_results = self.run_da_uc_market() # idle -> bid
            da_results = self.run_da_uc_market() # bid -> clear
            da_results = self.run_da_uc_market() # clear -> idle
            #write results to file
            # self.markets[market].clear_market()
            filename = file_name + str(t) + ".json"
            self.markets[market].em.save_model(filename)
            # with open(filename, "w") as file:
            #     file.write(self.markets[market].em.mdl_sol)
            print("Saved file as " + filename)

def run_osw_tso(start: str="2032-01-01 00:00:00", end: str="2032-1-03 00:00:00"):        #h5filepath: str, 
# if __name__ == "__main__":
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
            "initial_offset":  0,
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
                      #"reserves": da_market_timing,
                      "rt": rt_market_timing}
    
    # I don't think we will ever use the "last_market_time" values 
    # but they will give us confidence that we're doing things correctly.
    
    h5filepath = "C:\\Users\\kell175\\pyenergymarket\\data_model_tests\\data_files\\WECC240_20240807.h5"
    default_dam = {
        "time": {
            "datefrom": start
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
    solver = "cbc" # "gurobi" or "cbc"
    gv = pyen.GVParse(h5filepath, default=default_dam, logger_options={"level": loglevel})

    default_rtm = {
        "time": {
            "datefrom": start
        },
        "interpolate": {
            "method": 'linear' #None, zero -- options in scipy.interpolate
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
    loglevel = "WARNING"
    gv_rt = pyen.GVParse(h5filepath, default=default_rtm, logger_options={"level": loglevel})


    # Initalize pyenergymarkets for day ahead and real time energy markets.
    markets = {}
    pyenconfig_dam = {
        "time": {
            "datefrom": start, # whole year
            "dateto": end,
            'min_freq': 60, #15 minutes
            'window': 2,
            'lookahead': 0
        },
        "solve_arguments": {
            "kwargs":{
                "solver_tee": True # change to False to remove some logging
            }
        }
    }

    em_dam = pyen.EnergyMarket(gv, pyenconfig_dam)

    pyenconfig_rtm = {
        "time": {
            "datefrom": start, 
            "dateto": end,
            'min_freq':15, # 15 minutes
            'window':1,
            'lookahead':1
        },
        "solve_arguments": {
            "solver": "cbc",
            "solver_tee": False, # change to False to remove some logging
            "OutputFlag": 0,  # Gurobi-specific option to suppress output
            "solver_options": {
                "solver_tee": False,
                "OutputFlag": 0  # Gurobi-specific option to suppress output
            },
            "kwargs":{
                "solver_tee": False
                # "OutputFlag": 0  # Gurobi-specific option to suppress output
            }
        }
    }
    em_rtm = pyen.EnergyMarket(gv, pyenconfig_rtm)

    markets["da_energy_market"] = OSWDAMarket(start, end, "da_energy_market", market_timing["da"], market=em_dam)
    # Note that for now the reserves markets are operated when we run the day ahead energy market model, but I left the comment to remind us this may change.
    # markets["reserves_market"] = OSWReservesMarket("reserves_market", market_timing["reserves"])
    markets["rt_energy_market"] = OSWRTMarket(start, end, "rt_energy_market", market_timing["rt"], min_freq=15, market=em_rtm)
    return market_timing, markets, solver
    # osw = OSWTSO("WECC_market", market_timing, markets, solver=solver)
    # market = "da_energy_market"
    # osw.run_market_loop(market, "da_market_results_")
    # osw.run_market_loop(market, 'C:\\Users\\kell175\\copper\\run\\python\\results\\da_results_')


if __name__ == "__main__":    
    if sys.argv.__len__() > 2:
        market_timing, markets, solver = run_osw_tso() #(sys.argv[3]) #, sys.argv[4], sys.argv[5])
        wecc_market_fed = OSWTSO(sys.argv[1], market_timing, markets, solver=solver)
        wecc_market_fed.create_federate(sys.argv[2])
        wecc_market_fed.run_cosim_loop()
        wecc_market_fed.destroy_federate()