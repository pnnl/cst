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
        self.fullWS = TC.get_wind_data()

        # Set simulation start time
        self.sim_start_time = pd.Timestamp(datetime.datetime(2018, 1, 1, 0, 0, 0))
    
    def generate_wind_forecasts(self) -> list:
        """
        The T2 controller needs 30 wind forecast profiles to run their 
        optimization thus we generate them
        """
        num = 10 #choose 30 wind forecasts
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
            # self.wind_forecast = self.generate_wind_forecasts()


            self.wind_forecast = np.array([
            [10.0963, 10.0317, 10.0279, 10.1132, 9.79648, 10.0508, 9.8817, 9.87439, 9.81628, 9.88726],
            [9.74869, 9.70024, 9.74298, 9.84126, 9.7398, 9.71648, 9.76167, 9.7877, 9.83838, 9.70947],
            [9.64252, 9.73433, 9.68173, 9.51498, 9.71195, 9.64707, 9.78522, 9.73222, 9.47606, 9.51656],
            [9.17087, 9.22921, 9.15802, 9.35142, 9.1684, 9.13954, 9.091, 9.06294, 9.20547, 9.11692],
            [9.83787, 9.6873, 9.71677, 9.57371, 9.69057, 9.61541, 9.59954, 9.85609, 9.7466, 9.65246],
            [9.41441, 9.35905, 9.31663, 9.16367, 9.1613, 9.22182, 9.35539, 9.24689, 9.44361, 9.25764],
            [10.7817, 10.8963, 10.8681, 11.1015, 10.8995, 10.9464, 10.9196, 10.7702, 10.9776, 11.119],
            [10.99, 10.7557, 11.0623, 10.9104, 10.9997, 11.0318, 10.8639, 10.8355, 11.0253, 10.7888],
            [11.9949, 11.9543, 11.9118, 11.7822, 11.9482, 11.984, 11.7978, 11.9985, 12.1525, 11.8368],
            [11.7503, 11.7087, 11.761, 11.4376, 11.5465, 11.6359, 11.6977, 11.5827, 11.5163, 11.5738],
            [12.2877, 12.276, 12.3351, 12.397, 12.3869, 12.2885, 12.2665, 12.4948, 12.4353, 12.3665],
            [12.001, 12.034, 11.9039, 12.1014, 12.164, 11.9582, 12.0895, 11.9345, 12.0012, 11.8847],
            [12.0058, 12.2393, 12.022, 12.2608, 12.206, 12.0037, 11.9535, 12.1866, 11.9213, 12.1836],
            [11.9185, 11.7645, 11.6358, 11.6759, 11.5396, 11.8745, 11.6812, 11.854, 11.7449, 11.6406],
            [11.9374, 11.9418, 11.8638, 11.9217, 11.8786, 11.8295, 12.1399, 11.6743, 11.9089, 11.9788],
            [12.1439, 12.1453, 12.2969, 12.3302, 12.3411, 12.2531, 12.2825, 12.251, 12.2327, 12.2703],
            [11.8791, 11.8161, 11.7484, 11.8857, 11.9122, 11.7062, 11.7645, 11.8028, 11.9385, 11.787],
            [11.7805, 11.6927, 11.568, 11.6999, 11.7848, 11.7309, 11.6643, 11.6766, 11.7412, 11.4758],
            [11.8834, 11.7277, 11.8027, 11.6843, 11.7734, 11.8286, 11.7933, 11.8829, 11.8454, 11.6755],
            [11.8221, 11.8125, 11.8017, 11.7444, 11.7327, 11.9563, 11.6254, 12.0496, 11.8047, 11.8655],
            [11.7533, 11.6921, 11.6483, 11.7717, 11.8565, 11.6949, 11.6789, 11.7889, 11.7506, 11.7424],
            [12.2422, 12.354, 12.2721, 12.3444, 12.3294, 12.2314, 12.1218, 12.2079, 12.1288, 12.1862],
            [12.7999, 12.7845, 12.9517, 12.8531, 12.8652, 12.9444, 12.8876, 12.9018, 12.8707, 12.8556],
            [11.2709, 11.2696, 11.1437, 11.3696, 11.3335, 11.2868, 11.2705, 11.2384, 11.2221, 11.2543]
        ])
            self.wind_forecast = self.wind_forecast.T
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

        elif np.mod(Time.minute, 20) == 0:
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