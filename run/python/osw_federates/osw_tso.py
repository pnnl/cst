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
import copy
import json
import cosim_toolbox
import numpy as np

# internal packages
import pyenergymarket as pyen
from egret.data.model_data import ModelData

from cosim_toolbox.federate import Federate
from cosim_toolbox.dbResults import DBResults
from pyenergymarket.marketmodels.osw_da_market import OSWDAMarket
from pyenergymarket.marketmodels.osw_rt_market import OSWRTMarket
# from osw_reserves_market import OSWReservesMarket

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

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
    
    This class assumes that the EGRET functionality is presented in a
    class- or library-oriented method such that the market operation 
    methods can be called as stand-alone operations. 
    """

    def __init__(self, fed_name, market_timing, markets:dict={}, options=None, **kwargs):
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
        self.publish_model = options['simulation']['publish_model']
        self.pre_simulation_days = options['simulation']['pre_simulation_days']

        # I don't think we will ever use the "last_market_time" values 
        # but they will give us confidence that we're doing things correctly.

        # Set up the timeseries database
        self.dl = DBResults()
        self.dl.open_database_connections()
        self.dl.check_version()
        # if self.dl.table_exist(self.scenario['osw_test_schema'], "htd_double"):
        #     self.dl.create_schema(self.scenario['osw_test_schema'])
        #     self.dl.make_logger_database(self.scenario['osw_test_schema']) 

        self.market_timing = market_timing
        self.markets = self.calculate_initial_market_times(self.markets)
        # print("tso init:", self.markets["rt_energy_market"].em.configuration["time"]["min_freq"])

        self.wind_data = self.pull_data_from_db("osw_era5_schema","windspeeds")
        # print("WIND DATA:", self.wind_data)

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
            # print(market_name, last_state_time, next_state_time)
        return markets

    def enter_initialization(self):
        """
        Overload of Federate class method

        Prior to entering the HELICS initialization mode, we need to read
        in the model and do some initialization on everything
        """

        # self.read_power_system_model()
        self.initialize_power_and_market_model()
        self.hfed.enter_initializing_mode() # HELICS API call
        # Publish the initial DA Market prices
        super().send_data_to_federation()

    # def read_power_system_model(self):
    #     """
    #     Reads in the power system model into the native EGRET format.

    #     This should probably return something, even if its self.something
    #     """
    #     ## Create an Egret "ModelData" object, which is just a lightweight
    #     ## wrapper around a python dictionary, from an Egret json test instance
    #     pass # right now this is done outside the class.
        
    def _clear_and_save(self, market, save=True, advance_timestep=True):
        """
        Forces a clear of the given market. If save=True will publish the data to the federation
        """
        self.markets[market].clear_market(advance_timestep=advance_timestep)
        if save:
            mkt_results = self.markets[market].market_results
            if market.startswith("da"):
                self._update_da_prices(mkt_results)
            elif market.startswith("rt"):
                self._update_rt_prices(mkt_results)
            else:
                raise ValueError(f"Market {market} does not have a price-saving method")

    def initialize_power_and_market_model(self, pre_simulation_days_default=1):
        """
        Initializes the power system and market models
        """

        '''
        # Specify the number of days to run before the simulation. Running at least one day helps ensure all
        # units are started up appropriately and avoids potential anomalous prices at the start of the simulation
        # Data from the pre-simulation days is not saved
        if not hasattr(self, 'pre_simulation_days'):
            pre_simulation_days = pre_simulation_days_default
        else:
            pre_simulation_days = self.pre_simulation_days
        # Check if the pre-simulation days kicks us back a year. If so, we will clear Jan 1 multiple times
        # without advancing the timestep
        advance_timestep = True
        mkt_start_year = self.markets["da_energy_market"].start_times[0].year
        pre_simulation_year = (self.markets["da_energy_market"].start_times[0] - datetime.timedelta(days=pre_simulation_days)).year
        if  pre_simulation_year < mkt_start_year:
            advance_timestep = False
        # For each pre-simulation day, run a DA market, pass commitments to RT market, then run RT
        # markets until the end of the day.
        for day in range(pre_simulation_days):
            logger.info(f"Clearing pre-simulation day {pre_simulation_days-day} before market start date")
            self._clear_and_save("da_energy_market", save=False, advance_timestep=advance_timestep)
            if "rt_energy_market" in self.markets.keys():
                # First pass DA market values through
                da_commitment = self.markets["da_energy_market"].commitment_hist
                self.markets["rt_energy_market"].join_da_commitment(da_commitment)
                # Also saving day-ahead solutions to RT for 1st RT initialization
                self.markets["rt_energy_market"].da_mdl_sol = self.markets["da_energy_market"].em.mdl_sol
                # Now loop through and clear RT markets at the given RT frequency
                num_rt = int((24*60)/self.markets["rt_energy_market"].em.configuration["min_freq"])
                for rt_mkt in range(num_rt):
                    logger.info(f"Clearing pre-simulation RT market {rt_mkt} of day -{pre_simulation_days-day}")
                    # TODO: This always runs the first RT interval - check if this is okay. Otherwise
                    # we can run all of the intervals then reset timestep to 0 at the end.
                    self._clear_and_save("rt_energy_market", save=False, advance_timestep=advance_timestep)
        '''

        # Run the first actual DA market, so the RT market has commitment
        logger.info("Clearing an initial day-ahead market")
        self.markets["da_energy_market"].clear_market()
        # Update prices for data sent to the federation
        da_results = self.markets["da_energy_market"].market_results
        self._update_da_prices(da_results)
        # Add commitment variables to real-time market and clear the first RT interval
        if "rt_energy_market" in self.markets.keys():
            # Commitment
            da_commitment = self.markets["da_energy_market"].commitment_hist
            self.markets["rt_energy_market"].join_da_commitment(da_commitment)
            # State-of-Charge
            self.markets["rt_energy_market"].storage_soc = self.markets["da_energy_market"].storage_soc
            # Also saving day-ahead solutions to RT for 1st RT initialization
            self.markets["rt_energy_market"].da_mdl_sol = self.markets["da_energy_market"].em.mdl_sol
            # Now run an initial RT market (required to properly sync timesteps) and send data to federation
            self.markets["rt_energy_market"].clear_market()
            rt_results = self.markets["rt_energy_market"].market_results
            self._update_rt_prices(rt_results)
        print("Finished initialization")

    def calculate_next_requested_time(self):
        """
        Overload of Federate class method
 
        When update_internal_model is run, it calls update_market on the
        market object which calculates the next state time (next market
        state). To calculate the next time request, we just need the
        minimum of these saved market states.
        """
        next_state_times = []
        for market_name, market in markets.items():
            _, next_state_time = market.calculate_next_state_time()
            next_state_times.append(next_state_time)
        self.next_requested_time = min(next_state_times)
        logger.debug("Requested time: ", self.next_requested_time)
        return self.next_requested_time

    def update_power_system_and_market_state(self):
        """
        Reads in time-series values and values received via HELICS and applies
        them appropriately to the power system model. May involve reading 
        "self.data_from_federation"
        """
        pass

    def pull_data_from_db(self,schema_name,table_name):
        """
        Pulls tabular data from postgreSQL by schema and table names and converts
        the tabular data into a pandas dataframe
        """
        connection = cosim_toolbox.cst_data_db
        connection['host'] = 'gage.pnl.gov'
        db_conn = self.dl._connect_logger_database()
        cursor = db_conn.cursor()
        query = f"SELECT * FROM {schema_name}.{table_name}"
        cursor.execute(query)
        rows = cursor.fetchall()
        colnames = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(rows,columns=colnames)
        # use datetime as index
        df.set_index('real_time', inplace=True)
        df.index = pd.to_datetime(df.index)
        return df

    def extract_one_day(self,df,timestamp):
        """
        Takes in full time series data and returns data for just one specified day
        """
        # timestamp = pd.to_datetime(day)
        timestamp = timestamp.replace(year = 2016)
        # print("timestamp: ", timestamp)
        # print(timestamp.year, timestamp.day)
        # return df[(df['real_time'].dt.year == timestamp.year) & (df['real_time'].dt.dayofyear == timestamp.day)]
        return df.loc[(df.index.year == timestamp.year) & (df.index.dayofyear == timestamp.dayofyear)]
        # return df.loc[timestamp]

    
    def interpolate_rt_wind_forecasts(self, current_day, next_day):
        wind_forecast_appended = pd.concat([current_day, next_day], axis = 0)
        interp_wind = wind_forecast_appended.resample('15min').interpolate('linear')
        try:
            day = current_day.index[0].day
            interp_wind = interp_wind.loc[interp_wind.index.day == day]
        except Exception as ex:
            print(ex)                        
                        
        print(f'INTERP WIND: {interp_wind}')

        return interp_wind


    def get_current_windspeed(self, timestamp, bus):
        curr_day_wind_data = self.extract_one_day(self.pull_data_from_db("osw_era5_schema","windspeeds"),timestamp)
        next_timestamp = timestamp + datetime.timedelta(days=1)
        next_day_wind_data = self.extract_one_day(self.pull_data_from_db("osw_era5_schema","windspeeds"), next_timestamp)

        current_windspeed = self.interpolate_rt_wind_forecasts(curr_day_wind_data, next_day_wind_data)
        # print(f'CURRENT WINDSPEED: {current_windspeed}')
        timestamp = timestamp.replace(year = 2016)
        current_windspeed = current_windspeed[bus].loc[timestamp]
        print(f'CURRENT WINDSPEED at BUS: {current_windspeed}')

        return current_windspeed


    def autocor_norm(self, av,st,le,au):
        # average, standard deviation, length, autocorrelation
        rn = np.random.normal(av,st,le)
        b = np.sqrt(1-au**2)
        rn_au = np.zeros(le)
        rn_au[0] = rn[0]
        for i in range(1,le):
            rn_au[i] = au*rn_au[i-1]+b*rn[i]
        return(rn_au)

    def generate_wind_forecasts(self, wind, num_forecasts = 30) -> list:
        """
        The T2 controller needs 30 wind forecast profiles to run their 
        optimization thus we generate them
        """
        forecast_list = []
        mu = 0 # 0 average -- no bias
        stdev = .02 # 2% standard deviation
        acor = 0.9 # 0.9 lag 1 autocorrelation
        wind_cap = wind.max()
        for i in range(num_forecasts):
            fcst = wind + self.autocor_norm(mu,stdev,len(wind),acor)*wind_cap
            forecast_list.append(fcst)    
        return np.array(forecast_list)
    


    def run_da_uc_market(self):
        """
        Using EGRET, clears the DA energy market in the form of a unit
        commitment optimization problem.

        TDH hopes this will be straight-forward and may take the form of calls
        to methods of an EGRET object.
        """
        # Get state time
        current_state_time = self.markets["da_energy_market"].update_market()
        # Move to next market state
        self.markets["da_energy_market"].move_to_next_state()
        # If it is a clearing state, clear the market and return the Egret ModelData results
        if self.markets["da_energy_market"].state == "clearing":
            return self.markets["da_energy_market"].market_results
        else:
            return current_state_time
        
    def run_reserve_market(self):
        """
        NOTE: Currently this is being run in the day ahead market.
        Using EGRET, clears the reserve market in the form of a unit
        commitment optimization problem.

        TDH hopes this will be straight-forward and may take the form of calls
        to methods of an EGRET object.
        """
        self.markets["reserve_market"].update_market()
        return self.markets["reserve_market"].market_results
       
    def run_rt_ed_market(self):
        """
        Using EGRET, clears the RT energy market in the form of an
        economic dispatch optimization problem.

        TDH hopes this will be straight-forward and may take the form of calls
        to methods of an EGRET object.
        """
        logger.debug(f"I MADE IT INTO RTM with state {self.markets['rt_energy_market'].state}")
        # Get the state time
        current_state_time = self.markets["rt_energy_market"].update_market()
        # Move state
        self.markets["rt_energy_market"].move_to_next_state()
        # If in clearing, clear the market and return the Egret ModelData results
        if self.markets["rt_energy_market"].state == "clearing":
            return self.markets["rt_energy_market"].market_results
        else:
            return current_state_time

    def _update_da_prices(self, da_results: ModelData, save_dispatch:bool=True):
        """
        Updates the day-ahead bus prices sent to the HELICS federation

        Args:
            da_results (Egret ModelData object): Egret model results from a cleared Day-ahead market
        """
        # area_keys = ['CALIFORN', 'MEXICO', 'NORTH', 'SOUTH']
        reserve_keys = ['regulation_up', 'regulation_down', 'flexible_ramp_up',
                      'flexible_ramp_down']
        for bus, b_dict in da_results.elements(element_type="bus"):
            new_dict = f"{b_dict['lmp']}"
            new_dict = new_dict.replace("'", '"')
            self.data_to_federation["publications"][f"{self.federate_name}/da_price_{bus[0:4]}"] = new_dict
        for area, area_dict in da_results.elements(element_type="area"):
            for key in reserve_keys:
                res_price_key = f"{key}_price" # Matches Egret naming convention
                reserve_dict = f"{da_results.data['elements']['area'][area][res_price_key]}"
                reserve_dict = reserve_dict.replace("'", '"')
                self.data_to_federation["publications"][f"{self.federate_name}/da_{key}_price_{area}"] = reserve_dict
        # Also can save the dispatch results from the market
        if save_dispatch:
            for gen, g_dict in da_results.elements(element_type="generator"):
                # Power/Energy
                dispatch = f"{g_dict['pg']}"
                dispatch = dispatch.replace("'", '"')
                self.data_to_federation["publications"][f"{self.federate_name}/da_dispatch_{gen}"] = dispatch
                # Reserves/Ancillary Services
                for key in reserve_keys:
                    supplied = f"{key}_supplied"
                    if supplied in g_dict.keys(): # Only save if the reserve is actually supplied by this gen
                        res_dispatch = f"{g_dict[supplied]}"
                        res_dispatch = res_dispatch.replace("'", '"')
                        self.data_to_federation["publications"][f"{self.federate_name}/da_{key}_dispatch_{gen}"] = \
                            res_dispatch
        if self.publish_model:
            results_string = json.dumps(da_results.data)
            self.data_to_federation["publications"][f"{self.federate_name}/da_model_results"] = results_string

    def _update_rt_prices(self, rt_results: ModelData, save_dispatch:bool=True):
        """
        Updates the real-time bus prices sent to the HELICS federation. Option to also save rt dispatch

        Args:
            ra_results (Egret ModelData object): Egret model results from a cleared real-time market
            save_dispatch (bool): Whether to save the real-time generator MW dispatch. Defaults to True
        """
        for bus, b_dict in rt_results.elements(element_type="bus"):
            new_dict = f"{b_dict['lmp']}"
            new_dict = new_dict.replace("'", '"')
            self.data_to_federation["publications"][f"{self.federate_name}/rt_price_{bus[0:4]}"] = new_dict
        if save_dispatch:
            for gen, g_dict in rt_results.elements(element_type="generator"):
                dispatch = f"{g_dict['pg']}"
                dispatch = dispatch.replace("'", '"')
                self.data_to_federation["publications"][f"{self.federate_name}/rt_dispatch_{gen}"] = dispatch
        if self.publish_model:
            results_string = json.dumps(rt_results.data)
            self.data_to_federation["publications"][f"{self.federate_name}/rt_model_results"] = results_string

    def update_internal_model(self, forecast_wind=False):
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

        print(f'DA market state: {self.markets["da_energy_market"].state}, {self.granted_time}')
        print(f'RT market state: {self.markets["rt_energy_market"].state}, {self.granted_time}')


        # Clear out values published last time (if there are any)
        for pub in self.data_to_federation["publications"]:
            self.data_to_federation["publications"][pub] = None
        for ep in self.data_to_federation["endpoints"]:
            self.data_to_federation["endpoints"][ep] = None

        # Check DA and RT markets - do a clearing as needed and publish data to federation
        self.update_power_system_and_market_state()
        if "da_energy_market" in self.markets.keys():
            if self.markets["da_energy_market"].next_state_time == round(self.granted_time):
            # if self.markets["da_energy_market"].next_state_time == round(self.granted_time) and ((self.stop_time - self.granted_time) > 600):
                if self.markets["da_energy_market"].state == "idle":
                    timestamp = pd.to_datetime(self.markets["da_energy_market"].current_start_time)
                    if forecast_wind:
                        curr_day_wind_data = self.extract_one_day(self.pull_data_from_db("osw_era5_schema","windspeeds"),timestamp)
                        print("one day wind data: ", curr_day_wind_data)
                        print(f'DA Market: {self.markets["da_energy_market"].current_start_time}')
                        try:
                            next_timestamp = timestamp + datetime.timedelta(days=1)
                            next_day_wind_data = self.extract_one_day(self.pull_data_from_db("osw_era5_schema","windspeeds"), next_timestamp)
                        except Exception as ex:
                            print(ex)

                        # cycle through offshore wind forecasts and publish generated forecasts lists
                        bus = 'bus_3234'
                        forecast_list = self.generate_wind_forecasts(curr_day_wind_data[bus]) # TODO Publish these for T2 (OSW_Plant) federate to subscribe to
                        print(f'forecast_list: {np.shape(forecast_list)} {forecast_list}')
                        self.data_to_federation["publications"][f"{self.federate_name}/wind_forecasts"] = str(forecast_list)

                # Grab the DAM start time before running UC (it moves to the 'next' start time as part of the clearing)
                dam = self.markets["da_energy_market"]
                this_start_time = dam.current_start_time
                # Run the unit commitment problem
                da_results = self.run_da_uc_market()
                
                # Enter bidding? Read results from osw_plant?? ---- move to collect bids?? leave (bcoz from federation) then pass to market
                if forecast_wind:
                    if self.markets["da_energy_market"].state == "bidding":
                        da_bid = self.data_from_federation["inputs"]['OSW_Plant/da_bids']
                        print(f'DA Bid: {da_bid}')

                #reserve_results = self.run_reserve_market()
                #self.data_to_federation["publication"][f"{self.federate_name}/da_clearing_result"] = da_results["prices"]["osw_node"]
                if self.markets["da_energy_market"].state == "clearing":
                    # Only run this if we are still within horizon (omit a potential final DA save/pass)
                    if this_start_time <= max(dam.start_times):
                        self._update_da_prices(da_results)
                        # Pass commitment and soc info on to real-time market, if it is present
                        if "rt_energy_market" in self.markets.keys():
                            da_commitment = self.markets["da_energy_market"].commitment_hist
                            self.markets["rt_energy_market"].join_da_commitment(da_commitment)
                            self.markets["rt_energy_market"].storage_soc = self.markets["da_energy_market"].storage_soc
                else:
                    print("da_next_time:", da_results)
                # = da_results["reserves_prices"]["osw_area"]
        
        
        if "rt_energy_market" in self.markets.keys():
            logger.debug("tso:", self.markets["rt_energy_market"].em.configuration["time"]["min_freq"])
            # Check if it is time to run the market
            if self.markets["rt_energy_market"].next_state_time == round(self.granted_time):
                if forecast_wind:
                    if self.markets["rt_energy_market"].state == "idle":
                        print(f'RT_Market: {self.markets["rt_energy_market"].current_start_time}')
                        rt_timestamp = pd.to_datetime(self.markets["rt_energy_market"].current_start_time)
                        # cycle through offshore wind forecasts and publish generated forecasts lists
                        bus = 'bus_3234'
                        current_windspeed = self.get_current_windspeed(rt_timestamp, bus)
                        self.data_to_federation["publications"][f"{self.federate_name}/wind_rt"] = str(current_windspeed)
                        print(f'current published windspeed: {current_windspeed}')
                        rt_bid = self.data_from_federation["inputs"]['OSW_Plant/rt_bids']
                        print(f'RT Bid: {rt_bid}')

                rt_results = self.run_rt_ed_market()
                # After a market run, update the prices to send to the HELICS federation
                if isinstance(rt_results, ModelData):
                    self._update_rt_prices(rt_results, save_dispatch=True)

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


def run_osw_tso(h5filepath: str, start: str="2032-01-01 00:00:00", end: str="2032-1-03 00:00:00",
                options: dict=None):
    #h5filepath: str,
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

    # Use adjustable minute frequency to allow variable-length RTM
    rtm_min_freq = options['market']['rt_min_freq']
    rtm_mkt_interval = rtm_min_freq * 60
    rt_market_timing = {
            "states": {
                "idle": {
                    "start_time": 0,
                    "duration": int(rtm_mkt_interval*2/3),
                },
                "bidding": {
                    "start_time": int(rtm_mkt_interval*2/3),
                    "duration": int(rtm_mkt_interval*0.2),
                },
                "clearing": {
                    "start_time": int(rtm_mkt_interval*2.6/3),
                    "duration": int(rtm_mkt_interval*0.4/3),
                }
            },
            "initial_offset":  0,
            "initial_state": "idle",
            "market_interval": rtm_mkt_interval
        }
    # Daily market with bidding beginning nine minutes before the end of 
    # the market interval and ending when clearing begins one minutee before 
    # the end of the interval.
    da_market_timing = {
            "states": {
                "idle": {
                    "start_time": 0,
                    "duration": 42660
                },
                "bidding": {
                    "start_time": 42660,
                    "duration": 540
                },
                "clearing": {
                    "start_time": 43200,
                    "duration": 43200
                },
            },
            "initial_offset": 0,
            "initial_state": "idle",
            "market_interval": 86400
        }
    market_timing = {
            "da": da_market_timing,
            #"reserves": da_market_timing,
            "rt": rt_market_timing
        }
    
    # I don't think we will ever use the "last_market_time" values 
    # but they will give us confidence that we're doing things correctly.

    # If adding pre-simulation days, modify the start time. OSWTSO will run these without saving
    # This allows all units to be turned on properly and avoids potential anomalous data early in the simulation
    start_year = pd.to_datetime(start).year
    pre_simulation_days = options['simulation']['pre_simulation_days']
    start = pd.to_datetime(start) - datetime.timedelta(days=pre_simulation_days)
    # PyEnergymarket doesn't automatically wrap year so we'll have special handling in osw_tso.py for Jan 1 start date
    if start.year < start_year:
        start += datetime.timedelta(days=pre_simulation_days)
    start = start.strftime("%Y-%m-%d %H:%M:%S")

    # h5filepath = "/Users/corn677/Projects/EComp/Thrust3/pyenergymarket/data_model_tests/data_files/WECC240_20240807.h5"
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
    loglevel = options['simulation']['loglevel_da']
    solver = options['simulation']['solver'] # "cplex", "cplexamp", "gurobi" or "cbc"
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
    loglevel = options['simulation']['loglevel_rt']
    gv_rt = pyen.GVParse(h5filepath, default=default_rtm, logger_options={"level": loglevel})


    # Initialize pyenergymarkets for day ahead and real time energy markets.
    markets = {}
    pyenconfig_dam = {
        "time": {
            "datefrom": start, # whole year
            "dateto": end,
            'min_freq': 60, #15 minutes
            'window': options['market']['da_window'],
            'lookahead': options['market']['da_lookahead'],
        },
        "solve_arguments": {
            "solver": solver,
            "solver_tee": False,
            "kwargs":{
                "solver_tee": True # change to False to remove some logging
            }
        }
    }

    em_dam = pyen.EnergyMarket(gv, pyenconfig_dam)
    #em_dam.configuration = copy.deepcopy(em_dam.configuration)
    pyenconfig_rtm = {
        "time": {
            "datefrom": start, 
            "dateto": end,
            'min_freq':options['market']['rt_min_freq'], # 15 minutes
            'window':options['market']['rt_window'],
            'lookahead':options['market']['rt_lookahead'],
        },
        "solve_arguments": {
            "solver": solver,
            "solver_tee": False, # change to False to remove some logging
            "OutputFlag": 0,  # Gurobi-specific option to suppress output
            "solver_options": {
                "OutputFlag": 0  # Gurobi-specific option to suppress output
            },
            "kwargs":{
                "solver_tee": False
                # "OutputFlag": 0  # Gurobi-specific option to suppress output
            }
        }
    }
    em_rtm = pyen.EnergyMarket(gv_rt, pyenconfig_rtm)

    if "da" in market_timing.keys():
        markets["da_energy_market"] = OSWDAMarket(start, end, "da_energy_market", market_timing["da"], market=em_dam,
                                              window=pyenconfig_dam["time"]["window"],
                                              min_freq=pyenconfig_dam["time"]["min_freq"],
                                              lookahead=pyenconfig_dam["time"]["lookahead"])
    # Note that for now the reserves markets are operated when we run the day ahead energy market model, but I left the comment to remind us this may change.
    # markets["reserves_market"] = OSWReservesMarket("reserves_market", market_timing["reserves"])
    if "rt" in market_timing.keys():
        markets["rt_energy_market"] = OSWRTMarket(start, end, "rt_energy_market", market_timing["rt"],
                                              min_freq=pyenconfig_rtm["time"]["min_freq"],
                                              window=pyenconfig_rtm["time"]['window'],
                                              lookahead=pyenconfig_rtm["time"]['lookahead'],
                                              market=em_rtm)
    
    return market_timing, markets, solver
    # osw = OSWTSO("WECC_market", market_timing, markets, solver=solver)
    # market = "da_energy_market"
    # osw.run_market_loop(market, "da_market_results_")
    # osw.run_market_loop(market, 'C:\\Users\\kell175\\copper\\run\\python\\results\\da_results_')

def get_options(use_defaults=False) -> dict:
    """ Gets the options from a json file (creating a new file if it doesn't exist).
    TODO: this mostly mirrors get_config from runner.py -> these both could probably be pushed to a utils.py later
    Args:
        use_defaults (bool, optional): Whether to use default options instead of json file. Defaults to False.
    ReturnsL
        options (dict): A dictionary of the relevant options.
    """
    def _write_options(new_options, exit_message=True):
        with open('options_osw.json', 'w') as f:
            json.dump(new_options, f, indent=4)
        if exit_message:
            print("Created file `options_osw.json` with default settings."
                  "\nEdit this file to customize your OSW settings.")
            exit(0)
    default_options = {'market': {'da_window': 24,
                                  'da_lookahead': 0,
                                  'rt_window': 1,
                                  'rt_lookahead': 4,
                                  'rt_min_freq': 15,
                                  },
                       'simulation': {'solver': 'gurobi',
                                      'pre_simulation_days': 1,
                                      'publish_model': False,
                                      'loglevel_da': "INFO",
                                      'loglevel_rt': "WARNING",}
                       }
    if use_defaults:
        return default_options

    # If not using defaults, read info from json. The first time through the code will be run with default settings
    if not os.path.exists("options_osw.json"):
        _write_options(default_options, exit_message=False)
    else:
        with open('options_osw.json', 'r') as f:
            options = json.load(f)
        # If new default options are added, write these to the existing config, but keep running
        for key in default_options.keys():
            if key not in options.keys():
                options[key] = default_options[key]
        _write_options(options, exit_message=False)
    return options

if __name__ == "__main__":    
    if sys.argv.__len__() > 2:
        import time
        t1 = time.time()
        osw_options = get_options()
        market_timing, markets, solver = run_osw_tso(sys.argv[3], sys.argv[4], sys.argv[5],
                                                     options=osw_options)
        wecc_market_fed = OSWTSO(sys.argv[1], market_timing, markets, options=osw_options)
        wecc_market_fed.create_federate(sys.argv[2])
        wecc_market_fed.run_cosim_loop()
        # wecc_market_fed.markets["da_energy_market"].em.data_provider.h5.close()
        # wecc_market_fed.markets["rt_energy_market"].em.data_provider.h5.close()
        wecc_market_fed.destroy_federate()
        t2 = time.time()
        print(f"Total simulation time: {t2 - t1:.2f} seconds")
 