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


# internal packages
from cosim_toolbox.federate import Federate
from cosim_toolbox.dbResults import DBResults

file_path = os.getcwd()
sys.path.append(os.path.join(file_path, "plant"))
from OnlineBidClass_NoReserve_tk import WindFarm as WF
from T2_Controller_Class import T2_Controller as TC

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
        self.wind_forecasts: list = None # wind forecasts
        self.wind_speed_current_period: float = None

        #keys for the subscriptions
        self.rt_dispatch: list = None # RT dispatch
        self.da_dispatch: list = None # DA dispatch
        self.res_dispatch: list = None # RES dispatch

        # initialize WF
        # self.OneWindFarm = TC.initialize_WindFarm()
        self.WF_inits = {}
        # get list of buses
        for bus in ['4005','3902','3903','4202', '3911' ]: #OSW buses
            self.WF_inits[f'bus_{bus}'] = TC.initialize_WindFarm(bus)

        # Set simulation start time
        self.sim_start_time = pd.Timestamp(datetime.datetime(2032, 1, 1, 0, 0, 0))
        self.sim_time = 0

        self.da_time = self.sim_start_time
        self.rt_time = self.sim_start_time

        self.prev_forecasts = np.zeros((30,24))
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
        jsonload = json.loads(self.data_from_federation["inputs"]['OSW_TSO/wind_forecasts'])
        # print("DA JSONLOAD: ", jsonload)
        try:
            self.da_time = pd.Timestamp(jsonload['time'])
            self.wind_forecasts = np.array(jsonload['forecast'])
            self.da_bus = jsonload['bus']
            # print("DA JSONLOAD: ", jsonload)

        except Exception as ex:
            # print('NWF error: ', ex)
            self.wind_forecasts = self.prev_forecasts

    def read_rt_wind(self):
        jsonload = json.loads(self.data_from_federation["inputs"]['OSW_TSO/wind_rt'])
        # print("RT JSONLOAD: ", jsonload)
        try:
            self.rt_time = pd.Timestamp(jsonload['time'])
            self.wind_rt = (jsonload['wind_rt'])
            self.rt_bus = jsonload['bus']
            # print("RT JSONLOAD: ", jsonload)

        except Exception as ex:
            # print('WRT error: ', ex)
            self.wind_rt = self.prev_wind_rt 

    # 
    def update_internal_model(self):

        self.read_published_forecasts()
        self.read_rt_wind()
        
        # Time = max(self.da_time, self.rt_time)
        # print('Granted time: ',  self.sim_start_time + datetime.timedelta(seconds = self.granted_time))
        # print('Time: ', Time)

        # if (np.sum(np.sum(self.prev_forecast)) != 0) & ((Time.hour == 0) & (Time.minute == 0)):
        # print('WF: ', self.wind_forecasts)
        # print('PF: ', np.sum(np.sum(self.prev_forecasts)), self.prev_forecasts)

        # if (np.sum(np.sum(self.prev_forecast)) != 0) & (len(self.wind_forecast)) & ((self.wind_forecast != self.prev_forecast).any()) & ((Time.hour == 0) & (Time.minute == 0)):
        # if (self.wind_forecast is not None) & ((self.wind_forecast != self.prev_forecast).any()) & ((Time.hour == 0) & (Time.minute == 0)):
        if self.wind_forecasts is None:
            self.wind_forecasts = self.prev_forecasts
        
        if ((self.wind_forecasts != self.prev_forecasts).any()):# & ((Time.hour == 0) & (Time.minute == 0)):

            # Generate DA Bid
            try:
                bus = self.da_bus
                self.da_bid = WF.create_day_ahead_energy_bid(self.WF_inits[bus], self.da_time, self.wind_forecasts)
                self.data_to_federation["publications"][f"{self.federate_name}/da_bids"] = str(self.da_bid)
                print(self.da_time, " ","DA Bid: ", self.da_bid)
            except Exception as ex:
                print('DA Bid Error: ', ex)

            # update prev_forecast
            self.prev_forecasts = self.wind_forecasts

        # # Generate RT Bid every 15 minutes --- start after 9:55am and go ad infinitum?
        # if 0:
        if self.rt_time.dayofyear > 1:
            if (self.prev_wind_rt != self.wind_rt) & (self.wind_rt >= 0):
                # print(f'WIND_RT: {self.wind_rt}')
                # print(f'RTM: {self.rt_time}')
                try:
                    bus = self.rt_bus
                    self.rt_bid = WF.create_real_time_energy_bid(self.WF_inits[bus], self.rt_time, self.wind_rt) 
                    self.data_to_federation["publications"][f"{self.federate_name}/rt_bids"] = str(self.rt_bid)
                    print(self.rt_time, "RT Bid: ", self.rt_bid, "WindSpeed: ", self.wind_rt )
                except Exception as ex:
                    print(f"RT Bid Error: {ex}")

                try:
                    bus = self.rt_bus
                    WF.create_dispatch(self.WF_inits[bus], self.rt_time+datetime.timedelta(minutes=1), [0,self.rt_bid], self.wind_rt)
                    print(self.rt_time+datetime.timedelta(minutes=1), ' Dispatched')
                except Exception as ex:
                    print(f"Dispatch Error: {ex}")

                #
                self.prev_wind_rt = self.wind_rt


if __name__ == "__main__":    
    if sys.argv.__len__() > 2:
        osw_plant_fed = OSWPLANT(sys.argv[1])
        osw_plant_fed.create_federate(sys.argv[2])
        osw_plant_fed.run_cosim_loop()
        osw_plant_fed.destroy_federate()