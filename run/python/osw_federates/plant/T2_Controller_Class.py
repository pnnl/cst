# -*- coding: utf-8 -*-
"""
Created on Sat Sep 21 20:07:52 2024

@author: wood200
"""

# %%
import pandas as pd
import numpy as np
from pyomo.environ import *
from pyomo.opt import SolverFactory
from datetime import datetime, timedelta
from scipy.stats import truncnorm
import random
import os 

from OnlineBidClass_tk import WindFarm as WF

# Assuming OnlineBid.py contains the translated Python module with necessary functions
# from OnlineBidClass import Turbine_PC, WindFarm, solve_DA_problem, create_day_ahead_energy_bid, create_real_time_energy_bid, create_reserve_bid, create_dispatch
# from helperFunctions import plotBids
# %% [markdown]
# # Prepare data for testing
class T2_Controller:

    def __init__():
        pass
    
    # %%
    def initialize_WindFarm():
        ##%%time
        RatedPower = 15
        breakpts = np.array([2.795492381350064, 7, 10.590504911515957, 25])
        f1_coef = [0.0800404, -0.229128, 0.0403189, 0.0112332]
        f2_coef = [-0.0352525, -0.346, 0.082, 0.008]
        coefs = np.hstack([np.zeros((4, 1)), np.array(f1_coef)[:, np.newaxis], np.array(f2_coef)[:, np.newaxis], np.vstack([RatedPower, np.zeros([3,1])]), np.zeros((4, 1))])
        
        # %
        ##%%time
        # Simulation setup
        VBase = 525
        PowerBase = 2350
        RBase = VBase**2 / PowerBase
        # np.random.seed(3)
        SW = 2350 / PowerBase
        
        # Electrical system parameters
        CS = 2600 / PowerBase  # Transmission cable capacity in per unit
        etaCh = 0.91  # BESS charging efficiency
        etaDis = 1 / 0.91  # BESS discharging efficiency
        DurH = 4  # Duration hour for the BESS
        DelfU = 0.25 / 60  # Delta f for up
        DelfD = 0.025 / 60  # Delta f for down
        Dist = 444.423  # Cable length in km
        Rrate = 0.0072  # Resistance rate in ohm/km
        
        # Calculation of g12 (conductance between bus 1 and 2)
        g12 = 1 / (Dist * Rrate / RBase)
        
        # Buses and voltage limits
        B = range(1, 3)  # set of buses
        Vmin = 0.9 * np.ones(len(B))  # Voltage minimum limit for each bus
        Vmax = 1.1 * np.ones(len(B))  # Voltage maximum limit for each
        # %
        ##%%time
        # Wind farm setup
        OneWindFarm = WF(15, breakpts, coefs, PowerBase, SW, B, Vmin, Vmax, CS, g12, 70.5/PowerBase, 141/PowerBase, etaCh, etaDis, DurH, DelfU)
    
        return OneWindFarm
    

    def get_wind_data():
        print(os.getcwd())
        file_path = os.getcwd()
        # WS = pd.read_csv("./data/WIND_Data_39.97_-128.77_2019_new.csv", header=0)
        WS = pd.read_csv(os.path.join(file_path, "plant", "data", "WIND_Data_39.97_-128.77_2019_new.csv"))
        fullWS = np.reshape(WS['Windspeed'],[24, int(len(WS['Windspeed'])/24)], order = 'F')

        return fullWS