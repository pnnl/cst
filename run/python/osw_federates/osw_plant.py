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
from cosim_toolbox.dataLogger import DataLogger

file_path = os.getcwd()
sys.path.append(os.path.join(file_path, "plant"))
from OnlineBidClass_tk import WindFarm as WF
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
        self.wind_forecast: list = None # wind forecasts
        self.wind_speed_current_period: float = None

        #keys for the subscriptions
        self.rt_dispatch: list = None # RT dispatch
        self.da_dispatch: list = None # DA dispatch
        self.res_dispatch: list = None # RES dispatch

        # initialize WF
        self.OneWindFarm = TC.initialize_WindFarm()
        
        # load yearlong wind information
        source = 6 ## while testing, select source of wind data
        self.fullWS = TC.get_wind_data(source)

        # Set simulation start time
        self.sim_start_time = pd.Timestamp(datetime.datetime(2018, 1, 1, 0, 0, 0))


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
    
    def generate_wind_forecasts(self) -> list:
        """
        The T2 controller needs 30 wind forecast profiles to run their 
        optimization thus we generate them
        """
        num = 10 #choose 'num' wind forecasts
        idx = random.sample(range(0,np.shape(self.fullWS)[1]), num) 
        wind_forecast = self.fullWS[:,idx].T

        return wind_forecast

    # 
    def update_internal_model(self):
        """
        """

        Time = self.sim_start_time + datetime.timedelta(seconds = self.granted_time)
        # print('Time: ', self.granted_time, Time)

        ## ONLY GENERATE ONE WIND_FORECAST DAILY???? -- adjust to one minute to adjust 
        if (Time.hour == 0) & (Time.minute == 1) & (Time.second == 0):
            self.wind_forecast = self.generate_wind_forecasts()
            print(Time, " ", self.wind_forecast)


        # Generate DA Bid at 11:56 AM
        if (Time.hour == 11) & (Time.minute == 56) & (Time.second == 0):
            print('Time: ', self.granted_time, Time)
            # wind_forecast = self.generate_wind_forecasts()
            self.da_bid = WF.create_day_ahead_energy_bid(self.OneWindFarm, Time, self.wind_forecast)
            print(Time, " ","DA Bid: ", self.da_bid)
        
        # Generate Reserves at 12:00 PM
        elif (Time.hour == 12) & (Time.minute == 0) & (Time.second == 0):
            # print('Time: ', self.granted_time, Time)
            # wind_forecast = self.generate_wind_forecasts()
            self.res_bid = WF.create_reserve_bid(self.OneWindFarm, Time, self.wind_forecast)
            print(Time, " ", "Reserve Bid: ", self.res_bid)

        # Generate RT Bid every 15 minutes --- start after 9:55am and go ad infinitum?
        if np.mod(Time.minute, 15) == 0:
            # wind_forecast = self.generate_wind_forecasts()
            # self.wind_speed_current_period = np.mean(np.mean(self.wind_forecast))
            # self.wind_speed_current_period = random.choice(random.choice(self.wind_forecast))
            self.wind_speed_current_period = random.choice(np.mean(self.wind_forecast, axis = 0))

            self.rt_bid = WF.create_real_time_energy_bid(self.OneWindFarm, Time, self.wind_speed_current_period)
            print(Time, "RT Bid: ", self.rt_bid, "WindSpeed: ", self.wind_speed_current_period )

            # store last RTM cleared HELICS time (float)
            self.RTM_mostrecent_cleared_period = self.granted_time

        # # dispatch 5 mins after RT bidding
        if (self.RTM_mostrecent_cleared_period > 0) & (self.granted_time == (self.RTM_mostrecent_cleared_period + 5*60)):
            WF.create_dispatch(self.OneWindFarm, Time, [0,self.rt_bid], self.wind_speed_current_period)
            # print("Dispatch: ", self.wind_speed_current_period )
            print(Time, ' Dispatched')




        #     # self.data_to_federation["publication"]["da_bids"] = WF.create_day_ahead_energy_bid(self.OneWindFarm, DA_RE_Time, WindSpeed)
        #     # self.data_to_federation["publication"]["res_bids"] = WF.create_reserve_bid(self.OneWindFarm, DA_RE_Time, WindSpeed)



    def send_data_to_federation(self) -> None:
        pass


if __name__ == "__main__":    
    if sys.argv.__len__() > 2:
        osw_plant_fed = OSWPLANT(sys.argv[1])
        osw_plant_fed.create_federate(sys.argv[2])
        osw_plant_fed.run_cosim_loop()
        osw_plant_fed.destroy_federate()