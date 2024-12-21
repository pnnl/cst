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
        print("osw_market", self.market_name, "start_times: ", self.start_times)
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
        implement the necessary operatations to update the market in question.
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

    def update_commitment_hist(self, keep='new'):
        """
        Updates the commitment and initial status of generators (and storage) based on the
        model solution from a cleared market.
        Args:
            keep (string): In the case of duplicate timestamps whether to keep 'new' or 'old' values. Defaults to new.
        """
        assert keep in ['new', 'old'], "keep must be either 'new' or 'old'"
        # Loop through all of the generators
        if not hasattr(self, 'commitment_hist'):
            self.commitment_hist = {}
        for etype, e_dict in self.em.mdl.data['elements'].items():
            # etype is 'generator', 'renewable', 'load', etc. - Egret types. e_dict holds each unit's info
            # Check that this element could be committed (optional - slight speedup but risk of missing new types
            if etype in ['generator', 'storage']:
                for unit, u_dict in e_dict.items():
                    # Add empty key if it doesn't already exist. Structure matches Egret (with timestamps added)
                    if etype not in self.commitment_hist.keys():
                        self.commitment_hist[etype] = {unit: {'commitment':
                                                              {'data_type': 'time_series',
                                                               'timestamps': [],
                                                               'values': []}}}
                    # Get current commitment_hist, then check for duplicate timestamps in the incoming solution
                    # This is expected for RT and for DA if using a lookahead window.
                    # We will use the new value (from the model) as the latest
                    # [Optional] Could clean this up with np.intersect1d or something
                    commit_times_hist = self.commitment_hist[etype][unit]['commitment']['timestamps']
                    commit_values_hist = self.commitment_hist[etype][unit]['commitment']['values']
                    commit_times_new = self.em.mdl['system']['time_keys']
                    commit_values_new = u_dict['commitment']['values']
                    for i, timestamp in enumerate(commit_times_new):
                        if timestamp in commit_times_hist:
                            if keep == 'new':
                                # Find the index of the previous value and overwrite it with the new value
                                hidx = commit_times_hist.index(timestamp)
                                commit_values_hist[hidx] = commit_values_new[i]
                        else:
                            commit_times_hist.append(timestamp)
                            commit_values_hist.append(commit_values_new[i])
                    # May be unnecessary, but ensuring that times are strictly ascending
                    sorted_inds = np.argsort(commit_times_hist)
                    commit_times_hist = list(np.array(commit_times_hist)[sorted_inds])
                    commit_values_hist = list(np.array(commit_values_hist)[sorted_inds])
                    self.commitment_hist[etype][unit]['commitment']['timestamps'] = commit_times_hist
                    self.commitment_hist[etype][unit]['commitment']['values'] = commit_values_hist

    def clear_market(self, hold_time=False, local_save=True):
        """
        Callback method that runs EGRET and clears a market.

        This method must be overloaded in an instance of this class to
        implement the necessary operates to clear the market in question.

        Args:
            hold_time (bool, optional): if True, the market will not advance the timestep
                                        This is intended for an initial market clearing only.
            local_save (bool, optional): if True, will save a JSON with the results at each timestep
        """
        self.em.get_model(self.current_start_time)
        self.em.solve_model()
        print(self.market_name, "self.em.mdl_sol:", self.em.mdl_sol)
        if local_save:
            with open(f'{self.market_name}_results_{self.timestep}.json', 'w') as f:
                json.dump(self.em.mdl_sol.data, f)
        self.market_results = self.em.mdl_sol
        self.update_commitment_hist()
        self.timestep += 1
        if self.timestep >= len(self.start_times):
            pass
        else:
            self.current_start_time = self.start_times[self.timestep]
        print("OSW ", self.market_name, "next start time: ", self.current_start_time)

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
        print(self.market_name, "Last state:", self.last_state)
        print(self.market_name, "Next state:", self.current_state)
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

    
