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
import numpy as np
from transitions import Machine
from osw_market import OSWMarket
from pyenergymarket.utils.timeutils import count_onoff, mk_daterange

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
    the activity of the market takes place at the transitions. I'm
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
        # Space for day-ahead solution (used at initialization)
        self.da_mdl_sol = None

    # def collect_bids(self, gen_commitment):
    #     """
    #     Callback method that pulls in bids to grid data and moves to the next state.

    #     This method must be overloaded in an instance of this class to
    #     implement the necessary operatations to update the market in question.
    #     """
    #     self.move_to_next_state()

        
    def interpolate_market_start_times(self, start_date, end_date, freq='15min', start_time=' 00:00:00'):
        """
        Overloaded method of OSWMarket:
        Interpolates 15 (by default) minute data between two date strings.
        """

        # Convert strings to datetime objects
        start_datetime = pd.to_datetime(start_date)# + start_time)
        end_datetime = pd.to_datetime(end_date)# - pd.Timedelta(freq)# + start_time)

        # Generate hourly datetime index
        start_time_index = pd.date_range(start_datetime, end_datetime, freq=freq, inclusive='left')
        return start_time_index

    def clear_market(self, local_save=False):
        """
        Callback method that runs EGRET and clears a market.

        This method must be overloaded in an instance of this class to
        implement the necessary operates to clear the market in question.
        """
        if self.current_start_time > max(self.start_times):
            logger.warning(f"RT Market: Current start time {self.current_start_time} is past horizon {max(self.start_times)}"
                        "Market will not be cleared")
            return
        self.em.get_model(self.current_start_time)
        if self.em.mdl_sol is not None:
            self.update_model_from_previous(self.em.mdl_sol)
        # If no solution (first pass) check for an initial day-ahead solution
        elif self.da_mdl_sol is not None:
            self.update_model_from_previous(self.da_mdl_sol, day_ahead_input=True)
        self.em.solve_model()
        self.market_results = self.em.mdl_sol
        self.update_commitment_hist()
        if local_save:
            self.em.save_model(f'{self.market_name}_results_{self.timestep}.json')

        self.timestep += 1
        if self.timestep >= len(self.start_times):
            # Add a day (exact value doesn't matter, just need something past the horizon)
            min_freq = self.em.configuration["min_freq"]
            self.current_start_time += datetime.timedelta(minutes=min_freq)
        else:
            self.current_start_time = self.start_times[self.timestep]

        # self.start_times = self.start_times.delete(0) # remove the first element
        # if len(self.start_times) > 0:
        #     self.current_start_time = self.start_times[0] # and then clock through to the next one

    def join_da_commitment(self, da_commitment):
        """
        Takes the day-ahead commitment schedule and interpolates onto the real-time intervals
        Commitment values are kept constant for each hour
        Default behavior is to NOT overwrite any existing values. This is intended to be run after each
        day-ahead market clearing to add the coming day's commitment values
        """
        # Duplicate day-ahead values onto the (likely) more frequent real-time intervals
        min_freq = self.em.configuration["min_freq"]
        # Update the da_commitment timestamps - add an hour to the last timestamp to ensure we go to the end of the day
        end = max(da_commitment["timestamps"])
        if isinstance(end, str):
            # Assumes format "YYYY-mm-dd HH:MM:SS". Convert to datetime, add hour, then convert back to str
            end = pd.to_datetime(end) + datetime.timedelta(hours=1)
            end = end.strftime('%Y-%m-%d %H:%M:%S')
        else: # Hopefully any other datetime form or this will fail
            end += datetime.timedelta(hours=1)
        # Note inclusive='left' ensures we do not get 00:00:00 on the next day (assuming 24hr input)
        da_timestamps_interp = pd.to_datetime(mk_daterange(start=min(da_commitment["timestamps"]),
                                            end=end, min_freq=min_freq, inclusive='left'))
        # Loop through all generators (Maybe create a separate function to launch this loop?)
        da_commitment_interp = {'timestamps': da_timestamps_interp}
        idx = 1
        for etype, edict in da_commitment.items():
            if etype != 'timestamps':
                for unit, u_dict in edict.items():
                    # Create dictionary structure the first time through
                    da_commitment_interp = self._prep_commitment_hist(da_commitment_interp, etype, unit)
                    # Call the fill_real_time function on this set of values
                    da_commitment_interp[etype][unit]['commitment']['values'] = (
                        self.fill_real_time(u_dict['commitment']['values']))
                    # Add initial status
                    da_commitment_interp[etype][unit]['initial_status'] = u_dict['initial_status']
        # Call method from the base class. Keep old ensures RT values aren't overwritten.
        # This will just add any new da_commitment values to the existing commitment history
        self.update_commitment_hist(keep='old', merge_dict=da_commitment_interp)

    def fill_real_time(self, da_list: list):
        """
        Takes a list of values from the (hourly) day-ahead market and copies into a longer
        list based on the real-time frequency in minutes. For example, if min_freq=15
        this will copy each hourly values four times.

        Args:
            da_list (list): list of any kind of value from market day-ahead market
        Returns:
            rt_list (list): list of values copied into the real-time frequency
        """
        min_freq = self.em.configuration["min_freq"]
        # Determine the number of times to copy values
        remainder = 60 % min_freq
        if remainder != 0:
            print(f"Warning: min_freq {min_freq} is not a divisor of 60. Results may be inaccurate")
        num_copy = int(60 / min_freq)
        # Use numpy arrays and repeat function for fast copying
        da_array = np.array(da_list)
        rt_array = da_array.repeat(num_copy)
        return list(rt_array)

    def update_model_from_previous(self, mdl_com:ModelData, day_ahead_input=False):
        """
        Pull last setpoint data from mdl_sol timeseries and
        update the current self.mdl with generator values from solution.
        """
        time_window = self.em.configuration['time']['window']
        lookahead = self.em.configuration['time']['lookahead']
        min_freq = self.em.configuration["min_freq"]
        logger.debug(f"Updating commitment history for RT market at timestep {self.timestep}"
                     f"(time is {self.current_start_time}")
        if (self.em.mdl is not None) and (mdl_com is not None):
            for g, g_dict in mdl_com.elements(element_type='generator'):
                # Initial power is the last power cleared in the previous window
                # If initializing from day-ahead initial power is same as day-ahead initial power
                if day_ahead_input:
                    self.em.mdl.data['elements']['generator'][g]['initial_p_output'] = g_dict['initial_p_output']
                else:
                    self.em.mdl.data['elements']['generator'][g]['initial_p_output'] = g_dict['pg']['values'][time_window - 1]
                # we should also update the q/reactive power, but this first test will be dc only
                # self.mdl.data['elements']['generator'][g]['initial_q_output'] = g_dict['qg']['values'][self.configuration['time']['window'] - 1]

                # Load the commitment history and find the index corresponding to the current time
                commit_hist = self.commitment_hist['generator'][g]
                if self.current_start_time in self.commitment_hist['timestamps']:
                    t0idx = np.where(self.current_start_time == np.array(self.commitment_hist['timestamps']))[0][0]
                else:
                    t0idx = len(self.commitment_hist['timestamps'])
                # Function to find initial status (number of hours the unit has been on or off)
                self.em.mdl.data['elements']['generator'][g]['initial_status'] = (
                    count_onoff(commit_hist, t0idx-1, min_freq=min_freq))
                # It's possible for t0idx in the last interval to have no commitments available.
                # If so, skip. Otherwise, pass the commitments for the appropriate window
                if t0idx < len(commit_hist['commitment']['values']):
                    # Setting 'commitment' (setting 'fixed_commitment' leads to infeasibilities)
                    commit_hist_window = commit_hist['commitment']['values'][t0idx:t0idx + time_window + lookahead]
                    self.em.mdl.data['elements']['generator'][g]['commitment'] = {'data_type':'time_series',
                                                                              'values': commit_hist_window}

        else:
            raise ValueError("no model currently loaded.")
    
