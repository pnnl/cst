"""
Created on 12/02/2024

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
import numpy as np
import random
import os


# internal packages
from cosim_toolbox.federate import Federate
from cosim_toolbox.dbResults import DBResults

file_path = os.getcwd()
sys.path.append(os.path.join(file_path, "plant"))
from OnlineBidClass_tk import WindFarm as WF
from T2_Controller_Class import T2_Controller as TC

from load_db_data import DB 

from create_synthetic_forecast import SF

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.ERROR)

class OSWPLANT(Federate):
    """
    """

    def __init__(self, fed_name="", schema="default", **kwargs):
        super().__init__(fed_name, **kwargs)

        #keys for publications
        self.rt_bid: float = None # RT Bids
        self.da_bid: list = None # DA Bids
        self.res_bid: list = None # RES Bids
        self.wind_forecast: list = None # wind forecasts
        self.wind_speed_current_period: float = None

        #keys for the subscriptions
        self.rt_dispatch: list = None # RT dispatch
        self.da_dispatch: list = None # DA dispatch
        self.res_dispatch: list = None # RES dispatch

        # initialize WF
        self.OneWindFarm = TC.initialize_WindFarm()
        
        # # load yearlong wind information
        # schema = "osw_era5_schema"
        # tables = ["windspeeds", "power_normalization"]
        # Data = DB().read_db_data(schema, tables)
        # self.windspeeds = Data['windspeeds']

        # get list of buses

        # Set simulation start time
        self.sim_start_time = pd.Timestamp(datetime.datetime(2020, 1, 1, 0, 0, 0))
        self.sim_time = 0

        self.prev_forecast = np.zeros((30,24))
        self.prev_wind_rt = -1000.00

        self.day_count = 0


        #State variables
        # self.windspeed: float = None
        # self.OSW_power_output: float = None
        # self.energystorage_SOC: float = None
        # self.energystorage_power_output: float = None
        self.RTM_mostrecent_cleared_quantity: float = None
        self.RTM_mostrecent_cleared_price: float = None
        self.RTM_mostrecent_cleared_period: float = 0   #timestamp
        self.DAM_mostrecent_cleared_quantity: float = None
        self.DAM_mostrecent_cleared_price: float = None
        self.reserve_mostrecent_cleared_quantity: float = None
        self.reserve_mostrecent_cleared_price: float = None
        # self.wind_forecast: float = None
        self.DAM_mostrecent_cleared_period: float = None  #both energy and reserves, timestamp


    def read_published_forecasts(self):
                # new_wind_forecast = np.fromstring(self.data_from_federation["inputs"]['OSW_TSO/wind_forecasts'], dtype = int, sep = ",")
        new_wind_forecasts = self.data_from_federation["inputs"]['OSW_TSO/wind_forecasts']
        try:
            new_wind_forecasts = np.fromstring(new_wind_forecasts.replace('[', '').replace(']', ''), sep=' ')[:,np.newaxis]
        except Exception as ex:
            print(ex)
        if len(new_wind_forecasts) >= 24:
            self.wind_forecasts = new_wind_forecasts.reshape(int(len(new_wind_forecasts)/24), 24)
        else:
            self.wind_forecasts = new_wind_forecasts

    def read_rt_wind(self):
        self.wind_rt = float(self.data_from_federation["inputs"]['OSW_TSO/wind_rt'])

    # 
    def update_internal_model(self):

        ## DIFF times for day ahead and RT???

        # self.granted_time = min(self.sim_time_rt, self.sim_time_da)
        self.granted_time = self.sim_time
        ## convert HELICS time to pandas datetime
        Time = self.sim_start_time + datetime.timedelta(seconds = self.granted_time)
        # _wind_forecast = self.data_from_federation["inputs"]['OSW_TSO/wind_forecasts']
        # wind_forecast = np.fromstring(_wind_forecast.replace('[', '').replace(']', ''), sep=' ')[:,np.newaxis]
        self.read_published_forecasts()
        wind_forecast = self.wind_forecasts

        self.read_rt_wind()
        # read_publ

        # if (len(wind_forecast) >= 24) & (np.sum(np.sum(wind_forecast - self.prev_forecast))!= 0):
        if (len(wind_forecast) >= 24) & ((wind_forecast != self.prev_forecast).any()):

            try:
                print(f"{Time}, {np.shape(wind_forecast)}, {wind_forecast}")
            except Exception as ex:
                print(ex)
            # Generate DA Bid
            self.da_bid = WF.create_day_ahead_energy_bid(self.OneWindFarm, Time, wind_forecast)
            self.data_to_federation["publications"][f"{self.federate_name}/da_bids"] = str(self.da_bid)
            print(Time, " ","DA Bid: ", self.da_bid)
        
            # Generate Reserves
            self.res_bid = WF.create_reserve_bid(self.OneWindFarm, Time, wind_forecast)
            self.data_to_federation["publications"][f"{self.federate_name}/res_bids"] = str(self.res_bid)
            print(Time, " ", "Reserve Bid: ", self.res_bid)

            # update reserves clearing
            reserve_clearing = [self.res_bid[n][2] for n in range(1,24)]
            # self.OneWindFarm.reserve_clearing[Dates.ceil(DTDA, Dates.Day)] = reserve_clearing;
            self.OneWindFarm.reserve_clearing[Time.ceil('D')] = reserve_clearing

            # update prev_forecast
            self.prev_forecast = wind_forecast

            # # update sim_time
            # self.sim_time += 60*60*24


        # # Generate RT Bid every 15 minutes --- start after 9:55am and go ad infinitum?
        if (self.prev_wind_rt != self.wind_rt) & (self.wind_rt >= 0):
            # print(f'WIND_RT: {self.wind_rt}')
            print(f'RTM: {Time}')
            try:
                self.rt_bid = WF.create_real_time_energy_bid(self.OneWindFarm, Time, self.wind_rt)
            except Exception as ex:
                print(f"RT: {ex}")

            self.data_to_federation["publications"][f"{self.federate_name}/rt_bids"] = str(self.rt_bid)
            print(Time, "RT Bid: ", self.rt_bid, "WindSpeed: ", self.wind_rt )

            try:
                WF.create_dispatch(self.OneWindFarm, Time, [0,self.rt_bid], self.wind_rt)
                print(Time, ' Dispatched')
            except Exception as ex:
                print(f"Dispatch: {ex}")

            #
            self.prev_wind_rt = self.wind_rt

            # update sim_time
            self.sim_time += 60*15


        #     # store last RTM cleared HELICS time (float)
        #     self.RTM_mostrecent_cleared_period = self.granted_time

        # # # dispatch 5 mins after RT bidding
        # if (self.RTM_mostrecent_cleared_period > 0) & (self.granted_time == (self.RTM_mostrecent_cleared_period + 5*60)):
        #     try:
        #         WF.create_dispatch(self.OneWindFarm, Time, [0,self.rt_bid], self.wind_speed_current_period)
        #         print(Time, ' Dispatched')
        #     except Exception as ex:
        #         print(f"Dispatch: {ex}")


if __name__ == "__main__":    
    if sys.argv.__len__() > 2:
        osw_plant_fed = OSWPLANT(sys.argv[1])
        osw_plant_fed.create_federate(sys.argv[2])
        osw_plant_fed.run_cosim_loop()
        osw_plant_fed.destroy_federate()