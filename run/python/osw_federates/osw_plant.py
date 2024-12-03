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
        self.rt_bids: list = None # RT Bids
        self.da_bids: list = None # DA Bids
        self.res_bids: list = None # RES Bids
        self.wind_forecasts: list = None # wind forecasts

        #keys for the subscriptions
        self.rt_dispatch: list = None # RT dispatch
        self.da_dispatch: list = None # DA dispatch
        self.res_dispatch: list = None # RES dispatch

        # initialize WF
        self.OneWindFarm = TC.initialize_WindFarm()
        self.fullWS = TC.get_wind_data()
    
    def generate_wind_forecasts(self) -> list:
        """
        The T2 controller needs 30 wind forecast profiles to run their 
        optimization thus we generate them
        """
        num = 30 #choose 30 wind forecasts
        idx = random.sample(range(0,np.shape(self.fullWS)[1]), num) 
    
        wind_forecast = self.fullWS[:,idx].T

        return wind_forecast


    def convert_helics_time(self):
        ## convert self granted time to datetime


        (days, remainder) = divmod(self.granted_time, 86400)
        (hours, remainder) = divmod(remainder, 3600)
        (minutes, seconds) = divmod(remainder, 60)

        # m, s = divmod(self.granted_time, 60)
        # h, m = divmod(m, 60)

        print(self.granted_time, int(minutes), int(hours))
        Time = pd.Timestamp(datetime.datetime(2018, 1, int(days), int(hours), int(minutes)))

        return Time


    # 
    def update_internal_model(self):
        """
        """
        # Time = self.convert_helics_time()
        # print('Time: ', self.granted_time, Time)
        
        # # insert market timing check for day ahead and reserves
        if np.mod(self.granted_time, 60*60*24) == 0: ### TEMP FIT ---- NEED TO FIX IN FUTURE


            wind_forecast = self.generate_wind_forecasts()
            
            DTDA = pd.Timestamp(datetime.datetime(2018, 1, 1, 11, 0)) + datetime.timedelta(seconds=self.granted_time)
            print("Time: ", DTDA )
            print("WindForecast: ", wind_forecast)
            print("DA Bid: ", WF.create_day_ahead_energy_bid(self.OneWindFarm, DTDA, wind_forecast))
            print("Reserve Bid: ", WF.create_reserve_bid(self.OneWindFarm, DTDA, wind_forecast))

            # self.data_to_federation["publication"]["da_bids"] = WF.create_day_ahead_energy_bid(self.OneWindFarm, DA_RE_Time, WindSpeed)
            # self.data_to_federation["publication"]["res_bids"] = WF.create_reserve_bid(self.OneWindFarm, DA_RE_Time, WindSpeed)



    def send_data_to_federation(self) -> None:
        pass


if __name__ == "__main__":    
    if sys.argv.__len__() > 2:
        osw_plant_fed = OSWPLANT(sys.argv[1])
        osw_plant_fed.create_federate(sys.argv[2])
        osw_plant_fed.run_cosim_loop()
        osw_plant_fed.destroy_federate()