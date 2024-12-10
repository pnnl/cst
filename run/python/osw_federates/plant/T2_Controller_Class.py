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
    

    def get_wind_data(source):
        print(os.getcwd())
        file_path = os.getcwd()

        if source == 0:
            WS = pd.read_csv(os.path.join(file_path, "plant", "data", "WIND_Data_39.97_-128.77_2019_new.csv"))
            fullWS = np.reshape(WS['Windspeed'],[24, int(len(WS['Windspeed'])/24)], order = 'F')
        elif source == 1:
            WS = pd.read_csv(os.path.join(file_path, "plant", "data", "WIND_Data_39.97_-128.77_2017.csv"), header = 1)
            fullWS = np.reshape(WS['wind speed at 100m (m/s)'],[24, int(len(WS['wind speed at 100m (m/s)'])/24)], order = 'F')
        elif source == 2:
            fullWS = np.array([
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
            ]).T
            

        return fullWS