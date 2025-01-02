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
import pandas as pd
import numpy as np
import copy
from transitions import Machine
from pyenergymarket import EnergyMarket
from pyenergymarket.utils.timeutils import mk_daterange


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

    def __init__(self, market_name, market_timing, start_date, end_date, market:EnergyMarket=None, **kwargs):
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
        self.start_times = self.interpolate_market_start_times(start_date, end_date)
        logger.info("osw_market", self.market_name, "start_times: ", self.start_times)
        self.timestep = 0
        self.current_start_time = self.start_times[self.timestep]
        self.last_state = None
        self.market_timing  = market_timing
        self.last_state_time = 0
        # self.next_state_time = None 
        self.next_state_time = 0
        self.market_results = {}
        self.state_list = list(market_timing["states"].keys())
        self.state_machine = Machine(model=self, states=self.state_list, initial=self.current_state)
        self.state_machine.add_ordered_transitions()
        # Adding definitions for state transition callbacks
        # "self.clear_market" is the name of the method called when entering
        # the "clearing" state
        # _e.g.:_ self.state_machine.on_enter_clearing("self.clear_market")
        self.state_machine.on_enter_bidding("collect_bids")
        self.state_machine.on_enter_clearing("clear_market")
        self.validate_market_timing(self.market_timing)
        self.commitment_hist = None
        

        # Define callback_functions
        # self.state_machine.on_enter_clearing("calc_transition_times")

        # Adding definitions for state transition callbacks
        # "self.clear_market" is the name of the method called when entering
        # the "clearing" state
        # _e.g.:_ self.state_machine.on_enter_clearing("self.clear_market")

        # This translates all the kwarg key-value pairs into class attributes
        self.__dict__.update(kwargs)

    def collect_bids(self):
        """
        Callback method that pulls in T2 bids to grid data.

        This method must be overloaded in an instance of this class to
        implement the necessary operations to update the market in question.
        """
        pass

    # def init_commitment_hist(self, init_default=1):
    #     """
    #     Creates dictionaries for commitment and initial status of generators (and storage).
    #     These are empty to start and will be appended as markets are cleared
    #     Args:
    #         init_default (Union[float, int]): starting status. Negative # = off  Defaults to 1
    #                                                            Positive # = on
    #     """
    #     if self.em is None:
    #         raise ValueError("Cannot set commitment/status dictionaries without a market model")
    #     else:
    #         # (Empty) history of commitments for all model elements with a commitment variable.
    #         # Using the same structure as Egret and looking at the data within the Egret model
    #         self.commitment_hist = {}
    #         for etype, e_dict in self.em.mdl.data['elements'].items():
    #             # etype is 'generator', 'renewable', 'load', etc. - Egret types. e_dict holds each unit's info
    #             # Check that this element could be committed (optional - slight speedup but risk of missing new types
    #             if etype in ['generator', 'storage']:
    #                 for unit, u_dict in e_dict.items():
    #                     self.commitment_hist[etype] = {unit: {'commitment':
    #                                                               {'data_type':'time_series',
    #                                                                'timestamps':[],
    #                                                                'values':[]}}}

    @staticmethod
    def _prep_commitment_hist(commitment_dict, etype, unit):
        """
        Creates an empty dictionary structure for the commitment history for a given element and generator/unit

        Args:
            etype (str): Type of element ('generator', 'storage', etc.)
            unit (str): Name of unit (typical use case is Egret generator name)
        """
        if etype not in commitment_dict.keys():
            commitment_dict[etype] = {unit: {'initial_status': None,
                                             'commitment':
                                                  {'data_type': 'time_series',
                                                   'values': []}}}
        if unit not in commitment_dict[etype].keys():
            commitment_dict[etype][unit] = {'initial_status': None,
                                            'commitment':
                                                 {'data_type': 'time_series',
                                                  'values': []}}
        return commitment_dict

    def update_commitment_hist(self, keep='new', merge_dict=None):
        """
        Updates the commitment and initial status of generators (and storage) based on the
        model solution from a cleared market. Stored in the self.commitment_hist dictionary
        This is a partial copy of the Egret generator element dictionary, specifically designed
        to hold and update commitment history (and initial status) as markets pass

        Args:
            keep (string): In the case of duplicate timestamps whether to keep 'new' or 'old' values. Defaults to new.
            merge_dict (dict): Option to merge a commitment history (typically merging DA into RT). Defaults to None.
                               Note, if merge_dict is specified, Egret model will be ignored. Keep='new' will use
                               the merge_dict values in case of duplicate timestamps.
        """
        assert keep in ['new', 'old'], "keep must be either 'new' or 'old'"
        # Create dict if needed with the timestamps as a top level key (shared by all generators/elements)
        if self.commitment_hist is None:
            self.commitment_hist = {'timestamps':[]}
        # Keep a copy of the old and the new timestamps
        commit_times_hist = self.commitment_hist['timestamps']
        if merge_dict is None:
            commit_times_new = pd.to_datetime(self.em.mdl_sol.data['system']['time_keys'])
        else:
            commit_times_new = merge_dict['timestamps']
        # Check whether to loop over stored PyEnergyMarket Model or an input model dictionary
        if merge_dict is None:
            loop_dict = self.em.mdl_sol.data['elements']
        else:
            loop_dict = merge_dict
        for etype, e_dict in loop_dict.items():
            # etype is 'generator', 'renewable', 'load', etc. - Egret types. e_dict holds each unit's info
            # Restrict to committable elements (optional - slight speedup but risk of missing new types
            if etype in ['generator']:
                for unit, u_dict in e_dict.items():
                    # Add empty key if it doesn't already exist. Structure matches Egret (with timestamps added)
                    self.commitment_hist = self._prep_commitment_hist(self.commitment_hist, etype, unit)
                    # First time through, set the initial status (this is fixed based on the starting initial_status)
                    if self.commitment_hist[etype][unit]['initial_status'] is None:
                        self.commitment_hist[etype][unit]['initial_status'] = u_dict['initial_status']
                    # Get current commitment_hist, then check for duplicate timestamps in the incoming solution
                    # This is expected for RT and for DA if using a lookahead window.
                    # We will use the new value (from the model) as the latest
                    # [Optional] Could clean this up with np.intersect1d or something
                    commit_values_hist = self.commitment_hist[etype][unit]['commitment']['values']
                    if merge_dict is None:
                        if 'commitment' in u_dict.keys():
                            commit_values_new = u_dict['commitment']['values']
                        else: # If missing, Egret accepts the None input for unfixed
                            commit_values_new = [None] * len(commit_times_new)
                    else:
                        commit_values_new = merge_dict[etype][unit]['commitment']['values']
                    _commit_times_hist = copy.copy(commit_times_hist)
                    for i, timestamp in enumerate(commit_times_new):
                        if timestamp in _commit_times_hist:
                            if keep == 'new':
                                # Find the index of the previous value and overwrite it with the new value
                                hidx = _commit_times_hist.index(timestamp)
                                commit_values_hist[hidx] = commit_values_new[i]
                        else:
                            _commit_times_hist.append(timestamp)
                            commit_values_hist.append(commit_values_new[i])
                    # May be unnecessary, but ensuring that times are strictly ascending
                    sorted_inds = np.argsort(_commit_times_hist)
                    _commit_times_hist = list(np.array(_commit_times_hist)[sorted_inds])
                    commit_values_hist = list(np.array(commit_values_hist)[sorted_inds])
                    # Set commitment values
                    self.commitment_hist[etype][unit]['commitment']['values'] = commit_values_hist
        self.commitment_hist['timestamps'] = _commit_times_hist

    def clear_market(self, local_save=False):
        """
        Callback method that runs EGRET and clears a market.

        This method must be overloaded in an instance of this class to
        implement the necessary operates to clear the market in question.

        Args:
            hold_time (bool, optional): if True, the market will not advance the timestep
                                        This is intended for an initial market clearing only.
            local_save (bool, optional): if True, will save a JSON with the results at each timestep
        """
        # Don't run market if this start time exceeds the start time list
        if self.current_start_time > max(self.start_times):
            # TODO: Validate this and add a version to the RT market (if needed...)
            logger.info(f"Current start time {self.current_start_time} is past horizon {max(self.start_times)}; "
                        "Market will not be cleared")
            return
        self.em.get_model(self.current_start_time)
        self.em.solve_model()
        if local_save:
            self.em.save_model(f'{self.market_name}_results_{self.timestep}.json')
        self.market_results = self.em.mdl_sol
        self.update_commitment_hist()
        self.timestep += 1
        if self.timestep >= len(self.start_times):
            # Add a day (exact value doesn't matter, just need something past the horizon)
            self.current_start_time += dt.timedelta(days=1)
        else:
            self.current_start_time = self.start_times[self.timestep]
        logger.info("OSW ", self.market_name, "next start time: ", self.current_start_time)

    def validate_market_timing(self, market_timing) -> None:
        """
        Validate that the provided market timing is self-consistent.
        """
        pass
    
    def move_to_next_state(self) -> str:
        """
        Transitions to the next state in the state machine and updates
        appropriate object parameters.
        """
        self.last_state = self.current_state
        self.next_state()
        # self.current_state = self.state_machine.state
        self.current_state = self.state
        logger.debug(self.market_name, "Last state:", self.last_state)
        logger.debug(self.market_name, "Next state:", self.current_state)
        # TODO Debug why logs don't make it to log but prints do
        logger.info(f"{self.market_name} moved from {self.last_state} to {self.current_state}")
        return self.current_state
        
    def calculate_next_state_time(self,
                            #    market_timing: dict,
                            #    current_state: str,
                            #    next_state_time: float,
                               ) -> tuple[float, float]:
        """
        Calculate the value of the next state in terms of simulation time
        based on the timing of the next state in the state machine.
        """
        # Check - if we've reached the end, next time is returned as -1
        # print("Timestep", self.timestep, " Start times:", self.start_times)
        # if self.timestep >= len(self.start_times):
        #     return self.current_start_time, -999
        last_state_time = self.last_state_time
        self.next_state_time = self.market_timing["states"][self.current_state]["duration"] \
                            + last_state_time \
                            + self.market_timing["initial_offset"]
       
        # Rather than checking to see if its zero before setting it to zero,
        # just set it to zero (even if it already was.) The only time this
        # needs to be non-zero is the first time we do the first transition
        self.market_timing["initial_offset"] = 0
        logger.info(f"{self.market_name}.next_state_time: {self.next_state_time}")
        return last_state_time, self.next_state_time
 

    def update_market(self):
        """
        This method drives the state machine which drives all the other
        functionality via callbacks.

        An earlier version of this received the simulation time and checked
        to see if it was time to move to the next market state. For now
        that check is done by the instantiating object and it is assumed
        when this method is called, it's time to move to the next state
        """
        _, self.last_state_time = self.calculate_next_state_time()
        return self.last_state_time # current time

    def interpolate_market_start_times(self, start_date, end_date, freq='24h', start_time=' 00:00:00'):
        """Interpolates 24 (by default) hourly data between two date strings."""

        # Convert strings to datetime objects
        start_datetime = pd.to_datetime(start_date + start_time)
        end_datetime = pd.to_datetime(end_date + start_time)

        # Generate hourly datetime index
        start_time_index = pd.date_range(start_datetime, end_datetime, freq=freq, inclusive='left')
        return start_time_index

    
