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

from OnlineBidClass_NoReserve_tk import WindFarm as WF

# Assuming OnlineBid.py contains the translated Python module with necessary functions
# from OnlineBidClass import Turbine_PC, WindFarm, solve_DA_problem, create_day_ahead_energy_bid, create_real_time_energy_bid, create_reserve_bid, create_dispatch
# from helperFunctions import plotBids
# %% [markdown]
# # Prepare data for testing
class T2_Controller:

    # def __init__():
    #     pass
    
    # %%
    def initialize_WindFarm(bus_num:str = '4202'):

        # wind turbine power curve
        TurbMax = 15
        breakpts = np.array([2.795492381350064, 7, 10.590504911515957, 25])
        f1_coef = [0.0800404, -0.229128, 0.0403189, 0.0112332]
        f2_coef = [-0.0352525, -0.346, 0.082, 0.008]
        coefs = np.hstack([np.zeros((4, 1)), np.array(f1_coef)[:, np.newaxis], np.array(f2_coef)[:, np.newaxis], np.vstack([TurbMax, np.zeros([3,1])]), np.zeros((4, 1))])
        
        # common parameters
        RatedPower = 1 # wind farm rated power in p.u.
        B = range(1, 3)  # set of buses
        Vmin = 0.9 * np.ones(len(B))  # Voltage minimum limit for each bus
        Vmax = 1.1 * np.ones(len(B))  # Voltage maximum limit for each
        CabCap = 1.1  # Transmission cable capacity in per unit
        BatSize = 0.05 # BESS size in p.u.
        SoC = 0.1 # BESS initial SoC in p.u.
        etaCh = 0.91  # BESS charging efficiency
        etaDis = 1 / 0.91  # BESS discharging efficiency
        DurH = 4  # Duration hour for the BESS

        # common parameters not directly used
        VBase = 500 # voltage base
        Rrate = 0.0072  # Resistance rate in ohm/km

        if bus_num == '4005': #JOHNDAY
            PowerBase = 2350
            Dist = 444.423 # Cable length in km
        elif bus_num == '3902': #MOSSLAND
            PowerBase = 1800
            Dist = 660.732 # Cable length in km
        elif bus_num == '3903': #TESLA
            PowerBase = 2640
            Dist = 603.598 # Cable length in km
        elif bus_num == '4202': #WCASCADE
            PowerBase = 1500
            Dist = 545.060 # Cable length in km
        elif bus_num == '3911': #COTWDPGE
            PowerBase = 1810
            Dist = 324.193 # Cable length in km
        
        RBase = VBase**2 / PowerBase
        g = 1 / (Dist * Rrate / RBase)
        OneWindFarm = WF(TurbMax, breakpts, coefs, PowerBase, RatedPower, B, Vmin, Vmax, CabCap, g, BatSize, SoC, etaCh, etaDis, DurH)
        return OneWindFarm
    

    