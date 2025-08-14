"""
Created on 06/28/2024

Class market objects in Egret

This assumes EGRET functionality has been implemented as class functions that 
can be called as methods. (This may not be a hard assumption.)


@author: Trevor Hardy
trevor.hardy@pnnl.gov
"""
import datetime
import json
import logging
import pandas as pd
from transitions import Machine
from osw_market import OSWMarket
from pyenergymarket.utils.timeutils import count_gen_onoff_periods

# from typing import TYPE_CHECKING
# if TYPE_CHECKING:
from egret.data.model_data import ModelData

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.WARNING)

class OSWRTMarket(OSWMarket):
    """
    TODO: describe this class

    For the off-shore-wind use case, we only need three market states so
    those will be hard-coded as below. The way this market works, all of 
    the activity of the market takes place at the transisitions. I'm 
    (TDH) using the "transitions" library which allows the definition
    of callback functions when entering (and exiting) any given state
    and this is the primary method by which the activity will in the
    market will take place. 

    Documentation on the "transitions" library can be found here:
    https://pypi.org/project/transitions/



    """

    def __init__(self, start_date, end_date, market_name:str="rt_energy_market", market_timing:dict=None, min_freq:int=15, window:int=4, **kwargs):
        """
        Class that specifically runs the OSW RT energy market

        The only specialization is the definition of the callback method
        that gets called when the market state machine enters the "clearing"
        state.
        """
        super().__init__(market_name, market_timing, start_date, end_date, **kwargs)
        self.em.configuration["min_freq"] = min_freq
        self.em.configuration["window"] = window
        self.__dict__.update(kwargs)
        if self.market_timing == None:
            self.market_timing = {
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
            # starts at midnight
        self.start_times = self.interpolate_market_start_times(start_date, end_date)

        
    def interpolate_market_start_times(self, start_date, end_date, freq='15min', start_time=' 00:00:00'):
        """
        Overloaded method of OSWMarket:
        Interpolates 15 (by default) minute data between two date strings.
        """

        # Convert strings to datetime objects
        start_datetime = pd.to_datetime(start_date)# + start_time)
        end_datetime = pd.to_datetime(end_date)# - pd.Timedelta(freq)# + start_time)

        # Generate hourly datetime index
        start_time_index = pd.date_range(start_datetime, end_datetime, freq=freq)
        return start_time_index

    # def clear_market(self):
    #     """
    #     Overloaded method of OSWMarket

    #     Grab all the bids and run the DA UC optimization and then return the results
        
    #     market_results is an attribute of the OSWMarket class
    #     """

    #     self.market_results = {}

    def clear_market(self):
        """
        Callback method that runs EGRET and clears a market.

        This method must be overloaded in an instance of this class to
        implement the necessary operates to clear the market in question.
        """
        self.em.get_model(self.current_start_time)
        if self.em.mdl_sol is not None:
            self.update_model_from_previous(self.em.mdl_sol)
        self.em.solve_model()
        self.market_results = self.em.mdl_sol
        self.timestep += 1
        self.current_start_time = self.start_times[self.timestep]

        # self.start_times = self.start_times.delete(0) # remove the first element
        # if len(self.start_times) > 0:
        #     self.current_start_time = self.start_times[0] # and then clock through to the next one


    def update_model_from_previous(self,mdl_com:ModelData):
        """
        Pull last (not including lookahead) setpoint data from mdl_sol timeseries and
        update the current self.mdl with generator values from solution.
        """
        time_window = self.em.configuration['time']['window']
        if (self.em.mdl is not None) and (mdl_com is not None):
            for g, g_dict in mdl_com.elements(element_type='generator'):
                self.em.mdl.data['elements']['generator'][g]['initial_p_output'] = g_dict['pg']['values'][time_window - 1]
                # we should also update the q/reactive power, but this first test will be dc only
                # self.mdl.data['elements']['generator'][g]['initial_p_output'] = g_dict['qg']['values'][self.configuration['time']['window'] - 1]
                self.em.mdl.data['elements']['generator'][g]['initial_status'] = count_gen_onoff_periods(g_dict['pg']['values'][:time_window])#*10
        else:
            raise ValueError("no model currently loaded.")
    
