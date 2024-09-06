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
from transitions import Machine
from osw_market import OSWMarket



logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.WARNING)

class OSWDAMarket(OSWMarket):
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

    def __init__(self, market_name:str="da_energy_market", market_timing:dict=None, min_freq:int=60, window:int=24, **kwargs):
        """
        Class the specifically runs the OSW DA energy market

        The only specialization is the definition of the callback method
        that gets called when the market state machine enters the "clearing"
        state.
        """
        super().__init__(market_name, market_timing, **kwargs)
        self.em.configuration["min_freq"] = min_freq
        self.em.configuration["window"] = window
        # This translates all the kwarg key-value pairs into class attributes
        self.__dict__.update(kwargs)
        # if market_timing isn't specified input default vaules.
        if self.market_timing == None:
            self.market_timing = {
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


# def clear_market(self):
#     """
#     Overloaded method of OSWMarket

#     Grab all the bids and run the DA UC optimization and then return the results
    
#     market_results is an attribute of the OSWMarket class
#     """
#     pass

    
