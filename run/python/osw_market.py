"""
Created on 06/28/2024

Class market objects in Egret

This assumes EGRET functionality has been implemented as class functions that 
can be called as methods. (This may not be a hard assumption.)


@author: Trevor Hardy
trevor.hardy@pnnl.gov
"""
import datetime as dt
import json
import logging
from transitions import Machine
from pyenergymarket import EnergyMarket



logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.WARNING)

class OSWMarket():
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


    Not to scale but the market timing looks like this:

        idle start       bidding start         clearing start       next
        |                |                     |                    idle start
        |                |                     |                    |
        |                |                     |                    |
        V                V                     V                    V
        *--idle dur------*-----bidding dur-----*--clearing dur------*

    """
    pass

    def __init__(self, market_name, market_timing, market:EnergyMarket=None, **kwargs):
        """
        Generic version of all the markets used in the E-COMP LDRD intiative.
        As such, this is fairly particular to those needs and is 
        correspondingly simple. When update_market is called, the market
        state machine moves to the next state and the time for the next
        market transition is called. This is all just logistics for running
        the market.

        The real magic of this happens when you sub-class this and add in
        callback methods that are called when entering particular states.
        
        """
        self.em = market
        self.market_name = market_name
        self.current_state = market_timing["initial_state"]
        self.last_state = None
        self.market_timing  = market_timing
        self.last_state_time = 0
        self.next_state_time = None 
        self.market_results = {}
        self.state_list = list(market_timing["states"].keys())
        self.state_machine = Machine(model=self, states=self.state_list, initial=self.current_state)
        self.state_machine.add_ordered_transitions(self.state_list)
        # Adding definitions for state transition callbacks
        # "self.clear_market" is the name of the method called when entering
        # the "clearing" state
        # _e.g.:_ self.state_machine.on_enter_clearing("self.clear_market")
        self.state_machine.on_enter_clearing("clear_market")
        self.validate_market_timing(self.market_timing)

        # Define callback_functions
        # self.state_machine.on_enter_clearing("calc_transition_times")

        # Adding definitions for state transition callbacks
        # "self.clear_market" is the name of the method called when entering
        # the "clearing" state
        # _e.g.:_ self.state_machine.on_enter_clearing("self.clear_market")

        # This translates all the kwarg key-value pairs into class attributes
        self.__dict__.update(kwargs)

    def clear_market(self):
        """
        Callback method that runs EGRET and clears a market.

        This method must be overloaded in an instance of this class to
        implement the necessary operates to clear the market in question.
        """
        self.em.get_model(self.datefrom)
        self.em.solve_model()
        self.market_results = self.em.mdl_sol

    def validate_market_timing(self, market_timing) -> None:
        """
        Validate that the provided market timing is self-consistent.
        """
        pass
    
    def move_to_next_state(self, state_machine: Machine) -> str:
        """
        Transitions to the next state in the state machine and updates
        appropriate object parameters.
        """
        self.last_state = self.current_state
        self.state_machine.next_state()
        self.current_state = self.state_machine.state
        logger.info(f"{self.market_name} moved from {self.last_state} to {self.current_state}")
        return self.current_state
        
    def calculate_next_state_time(self,
                               market_timing: dict,
                               current_state: str,
                               next_state_time: float,
                               ) -> tuple[float, float]:
        """
        Calculate the value of the next state in terms of simulation time
        based on the timing of the next state in the state machine.
        """
        last_state_time = next_state_time
        next_state_time = market_timing["states"][current_state]["duration"] \
                            + self.last_state_time \
                            + market_timing["initial_offset"]
        
        # Rather than checking to see if its zero before setting it to zero,
        # just set it to zero (even if it already was.) The only time this 
        # needs to be non-zero is the first time we do the first transition
        market_timing["initial_offset"] = 0
        logger.info(f"{self.market_name}.next_state_time: {self.next_state_time}")
        return last_state_time, next_state_time

    def update_market(self):
        """
        This method drives the state machine which drives all the other
        functionality via callbacks.

        An earlier version of this received the simulation time and checked
        to see if it was time to move to the next market state. For now
        that check is done by the instantiating object and it is assumed
        when this method is called, it's time to move to the next state
        """
        self.move_to_next_state(self.state_machine)
        self.last_state_time, self.next_state_time = self.calculate_next_state_time(self.next_state_time, 
                                                                                    self.current_state,
                                                                                    self.market_timing)
        return self.next_state_time



    
