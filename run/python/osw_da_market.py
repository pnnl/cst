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
    pass

    def __init__(self, market_name, market_timing, **kwargs):
        """
        Class the specifically runs the OSW DA energy market

        The only specialization is the definition of the callback method
        that gets called when the market state machine enters the "clearing"
        state.
        """
        super.__init__(market_name, market_timing, **kwargs)

        # This translates all the kwarg key-value pairs into class attributes
        self.__dict__.update(kwargs)


def clear_market(self):
    """
    Overloaded method of OSWMarket

    Grab all the bids and run the DA UC optimization and then return the results
    
    market_results is an attribute of the OSWMarket class
    """

    self.market_results = {}


    
