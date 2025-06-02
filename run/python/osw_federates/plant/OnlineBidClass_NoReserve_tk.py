from pyomo.environ import *
from pyomo.opt import SolverFactory, SolverStatus, TerminationCondition
import numpy as np
from datetime import datetime, timedelta

solver_choice = 'gurobi'
# solver_choice = 'ipopt'

class WindFarm:
    def __init__(self, TurbMax, breakpts, coefs, PowerBase, RatedPower, B, Vmin, Vmax, CabCap, g, BatSize, SoC, etaCh, etaDis, DurH):
        self.TurbMax = TurbMax      # wind turbine maximum output in MW
        self.breakpts = breakpts    # wind turbine power curve breaking points m/s
        self.coefs = coefs          # 4*n matrix containing coefficients of each piece-wise polynomial function
        self.PowerBase = PowerBase      # power base unit
        self.RatedPower = RatedPower    # wind farm rated power in p.u.
        self.B = B              # set of HVDC buses
        self.Vmin = Vmin        # voltage min limit in p.u.
        self.Vmax = Vmax        # voltage max limit in p.u.
        self.CabCap = CabCap    # transmission cable capacity in p.u.
        self.g = g              # cable conductance
        self.BatSize = BatSize  # battery size in p.u. (max charge/discharge rate)
        self.SoC = SoC          # state of charge of battery in p.u.
        self.etaCh = etaCh      # BESS charging efficiency
        self.etaDis = etaDis    # BESS discharging efficiency
        self.DurH = DurH        # BESS duration hour
        self.DABid = {}
        self.RTBid = {}
        self.Charge = {}
        self.Discharge = {}
        self.HisSoC = {}
        self.reserve_clearing = {}

        #State variables
        self.windspeed: float = None
        self.OSW_power_output: float = None
        self.energystorage_SOC: float = None
        self.energystorage_power_output: float = None
        self.RTM_mostrecent_cleared_quantity: float = None
        self.RTM_mostrecent_cleared_price: float = None
        self.RTM_mostrecent_cleared_period: float = None   #timestamp
        self.DAM_mostrecent_cleared_quantity: float = None
        self.DAM_mostrecent_cleared_price: float = None
        self.reserve_mostrecent_cleared_quantity: float = None
        self.reserve_mostrecent_cleared_price: float = None
        self.wind_forecast: float = None
        self.DAM_mostrecent_cleared_period: float = None  #both energy and reserves, timestamp

    # piece-wise polynomial power function of wind turbine
    # x in the input value of this function
    # breakpts are breaking points of pieces
    # coefs are coefficients of each piece
    def Turbine_PC(self, x, breakpts, coefs):
        assert np.all(np.diff(breakpts) >= 0), "Breakpoints must be sorted."
        b = np.searchsorted(breakpts, x, side='left')
        # b = max(min(b, len(breakpts) - 1), 0)
        return sum(coefs[i, b]*(x**i) for i in range(coefs.shape[0]))

    def solve_DA_problem(self, WS, Time, Weight):
        # WF is the wind farm
        # WS is a n*24 matrix, each column is a 24 vector representing one scenario of wind speed for 24 hours
        # Time is in the format of YYYY-MM-DDTHH:MM:SS for example 2018-01-01T10:00:00
        # Weight is the weight factor number in objective function
        model = ConcreteModel()
        # model.Params.TuneOutput = 3

        WP = np.array([[self.Turbine_PC(WS[i, j],self.breakpts, self.coefs) for j in range(WS.shape[1])] for i in range(WS.shape[0])]) / self.TurbMax * self.RatedPower

        T = range(1, 25)  # time indices set
        S = range(1,WP.shape[0]+1)  # scenario indices set
        B = self.B

        model.pDA   = Var(T, within=NonNegativeReals)               # power committed to DA market
        model.pDiff = Var(T, S, within=NonNegativeReals)            # absolute value of difference between DA biding and actual power provided
        model.pW    = Var(T, S, within=NonNegativeReals)            # actual wind power generation
        model.pWR   = Var(T, S, within=NonNegativeReals)            # actual power supply
        model.v     = Var(B, B, T, S, within=NonNegativeReals)      # v_i*v_j where v_i is the voltage of bus i
        model.SC    = Var(T, S, within=NonNegativeReals)            # state of charge of battery
        model.pDis  = Var(T, S, within=NonNegativeReals)            # discharged power of battery
        model.pCh   = Var(T, S, within=NonNegativeReals)            # charged power of battery
        
        # Constraints adapted from Julia to Pyomo
        model.cons1 = ConstraintList()
        for t in T:
            for s in S:
                model.cons1.add(model.pDiff[t, s] >= model.pDA[t] - model.pWR[t, s])
                model.cons1.add(model.pDiff[t, s] >= model.pWR[t, s] - model.pDA[t])
                model.cons1.add(model.pW[t, s] == (model.v[1, 1, t, s] - model.v[1, 2, t, s]) * self.g)
                model.cons1.add((model.pDis[t, s] - model.pCh[t, s]) - model.pWR[t, s] == (model.v[2, 2, t, s] - model.v[1, 2, t, s]) * self.g)
                for i in B:
                    model.cons1.add(model.v[i, i, t, s] <= self.Vmax[i-1] ** 2)
                    model.cons1.add(model.v[i, i, t, s] >= self.Vmin[i-1] ** 2)
                model.cons1.add(model.v[1, 2, t, s] ** 2 <= model.v[1, 1, t, s] * model.v[2, 2, t, s])
                model.cons1.add((model.v[1, 1, t, s] - model.v[1, 2, t, s]) * self.g <= self.CabCap)
                model.cons1.add(model.pW[t, s] <= WP[s - 1, t - 1])
                model.cons1.add(model.pW[t, s] >= 0)
                if t > 1:
                    model.cons1.add(model.SC[t, s] - model.SC[t - 1, s] == (self.etaCh * model.pCh[t, s] - self.etaDis * model.pDis[t, s]))
                model.cons1.add(model.pCh[t, s] <= self.BatSize)
                model.cons1.add(model.pDis[t, s] <= self.BatSize)
                model.cons1.add(model.SC[t, s] <= self.BatSize * self.DurH)
        for s in S:
            model.cons1.add(model.SC[1, s] - self.SoC == (self.etaCh * model.pCh[1, s] - self.etaDis * model.pDis[1, s]))

        model.cons1.add(sum(model.SC[len(T), s] for s in S) == 0.5 * self.BatSize * self.DurH * np.size(WP, 0))
        
        # Objective and solver initialization
        model.objective = Objective(expr=sum(model.pDA[t] for t in T) - Weight * sum(model.pDiff[t, s] for t in T for s in S) / np.size(WP, 0), sense=maximize)
        solver = SolverFactory(solver_choice)
        # solver = SolverFactory('ipopt')
        result= solver.solve(model, tee=False)
        if (result.solver.status == SolverStatus.ok) and (result.solver.termination_condition == TerminationCondition.optimal):
            # Store bidding results in the wind farm dictionaries
            self.DABid[Time] = np.array([model.pDA[t].value for t in T]) * self.PowerBase
        else:
            self.DABid[Time] = np.maximum(np.mean(WP, axis=0) * (1 - self.RatedPower / self.g / self.Vmax[0]**2), 0) * self.PowerBase

    # WF is the wind farm
    # the current_time is in the format of YYYY-MM-DDTHH:MM:SS for example 2018-01-01T10:00:00
    # SymRes is the rate between up and down reserve
    def create_day_ahead_energy_bid(self, current_time, wind_forecast, Weight=3):
        future_time = current_time.ceil('D')
        if future_time in self.DABid:
            DABid = self.DABid[future_time]
            return [[[0, DABid[i]], 0, DABid[i]] for i in range(24)]
        else:
            self.solve_DA_problem(wind_forecast, future_time, Weight)
            DABid = self.DABid[future_time]
            return [[[0, DABid[i]], 0, DABid[i]] for i in range(24)]

    def create_real_time_energy_bid(self, current_time, wind_speed_current_period, TimeInter = 15):
        # WF is the wind farm
        # TimeInter is the time interval between two biddings in minutes
        TimeLength = TimeInter / 60  # Time length in hours
        WP = self.Turbine_PC(wind_speed_current_period, self.breakpts, self.coefs) / self.TurbMax * self.RatedPower

        ### charge or discharge the battery if SoC is low or high
        pChR = 0
        pDisR = 0
        if self.SoC < 0.1 * self.BatSize * self.DurH and WP > 0.1 * self.BatSize:
            pChR = 0.05 * self.BatSize
        elif self.SoC > 0.9 * self.BatSize * self.DurH:
            pDisR = 0.05 * self.BatSize

        # Update the RT bidding result
        future_time = current_time.ceil('15min')
        current_day = current_time.floor('D')
        current_hour = current_time.hour

        model = ConcreteModel()
        # model.Params.TuneOutput = 3

        B = self.B
        model.pWR = Var(within=Reals)
        model.pW = Var(within=NonNegativeReals)
        model.v = Var(B, B, within=NonNegativeReals)
        model.SC = Var(within=NonNegativeReals)
        model.pDis = Var(within=NonNegativeReals)
        model.pCh = Var(within=NonNegativeReals)

        # Constraints
        model.cons = ConstraintList()
        model.cons.add(model.pW == (model.v[1, 1] - model.v[1, 2]) * self.g)
        model.cons.add(model.pCh == pChR)
        model.cons.add(model.pDis == pDisR)
        model.cons.add((model.pDis - model.pCh) - model.pWR == (model.v[2, 2] - model.v[1, 2]) * self.g)
        for i in B:
            model.cons.add(model.v[i, i] <= self.Vmax[i-1] ** 2)
            model.cons.add(model.v[i, i] >= self.Vmin[i-1] ** 2)
        model.cons.add(model.v[1, 2] ** 2 <= model.v[1, 1] * model.v[2, 2])
        model.cons.add((model.v[1, 1] - model.v[1, 2]) * self.g <= self.CabCap)
        model.cons.add(model.pW <= WP)
        model.cons.add(model.pW  >= 0)
        model.cons.add(model.pCh <= self.BatSize)
        model.cons.add(model.pDis <= self.BatSize)
        model.cons.add(model.SC <= self.BatSize * self.DurH)

        ### provide maximum power
        model.objective = Objective(expr=model.pWR, sense=maximize)

        ######## store bidding result in the dictionary and return it ###########
        solver = SolverFactory(solver_choice)
        # solver = SolverFactory('ipopt')
        result = solver.solve(model, tee=False)
        if (result.solver.status == SolverStatus.ok) and (result.solver.termination_condition == TerminationCondition.optimal):
            self.RTBid[future_time] = model.pWR.value * self.PowerBase
            self.Charge[future_time] = model.pCh.value * self.PowerBase
            self.Discharge[future_time] = model.pDis.value * self.PowerBase
            return model.pWR.value * self.PowerBase
        else:
            print("Solver Status: ", result.solver.status)
            self.RTBid[future_time] = max(WP * (1 - self.RatedPower/self.g/(self.Vmax[0]**2)), 0) * self.PowerBase
            self.Charge[future_time] = 0
            self.Discharge[future_time] = 0
            return self.RTBid[future_time]

    # Function to access real time bids
    def create_dispatch(self, current_time, RT_result, wind_speed_current_period, TimeInter = 15):
        # WF is the wind farm
        # TimeInter is the time interval between two biddings in minutes
        TimeLength = TimeInter / 60  # Time length in hours
        WP = self.Turbine_PC(wind_speed_current_period, self.breakpts, self.coefs) / self.TurbMax * self.RatedPower

        ########## get the hour of current time and corresponding RT bidding result #############
        future_time = current_time.ceil('15min')
        current_day = current_time.floor('D')
        current_hour = current_time.hour

        if future_time in self.RTBid:
            # pRT = self.RTBid[future_time]/self.PowerBase
            pChR = self.Charge[future_time]/self.PowerBase
            pDisR = self.Discharge[future_time]/self.PowerBase
            # Ensure that at least one of pChR or pDisR is zero
            if pChR < pDisR:
                pChR = 0
            else:
                pDisR = 0
        else:
            # pRT = WP
            pChR = 0
            pDisR = 0

        ###
        pRT = RT_result[1]/self.PowerBase

        model = ConcreteModel()
        # model.Params.TuneOutput = 3


        B = self.B
        model.pDiff = Var(within=Reals)                     # absolute value of difference between bidding and generation
        model.pWR = Var(within=Reals)                       # actual power supply
        model.pW = Var(within=NonNegativeReals)             # actual wind power generation
        model.v = Var(B, B, within=NonNegativeReals)  # v_i*v_j where v_i is the voltage of bus i
        model.SC = Var(within=NonNegativeReals)             # state of charge of battery
        model.pDis = Var(within=NonNegativeReals)           # discharged power of battery
        model.pCh = Var(within=NonNegativeReals)            # charged power of battery

        # Constraints
        model.cons = ConstraintList()
        ### difference between power supply and RT bid
        model.cons.add(model.pDiff >= pRT - model.pWR)
        model.cons.add(model.pDiff >= model.pWR - pRT)
        model.cons.add(model.pW == (model.v[1, 1] - model.v[1, 2]) * self.g)
        ### operate battery according to RT solution
        model.cons.add(model.pCh >= pChR)
        model.cons.add(model.pDis >= pDisR)
        model.cons.add(model.pCh * model.pDis == 0)
        model.cons.add((model.pDis - model.pCh) - model.pWR == (model.v[2, 2] - model.v[1, 2]) * self.g)
        for i in B:
            model.cons.add(model.v[i, i] <= self.Vmax[i-1] ** 2)
            model.cons.add(model.v[i, i] >= self.Vmin[i-1] ** 2)
        model.cons.add(model.v[1, 2] ** 2 <= model.v[1, 1] * model.v[2, 2])
        model.cons.add((model.v[1, 1] - model.v[1, 2]) * self.g <= self.CabCap)
        model.cons.add(model.pW <= WP)
        model.cons.add(model.pW >= 0)
        model.cons.add(model.SC - self.SoC == (self.etaCh * model.pCh - self.etaDis * model.pDis) * TimeLength)
        model.cons.add(model.pCh <= self.BatSize)
        model.cons.add(model.pDis <= self.BatSize)
        model.cons.add(model.SC <= self.BatSize * self.DurH)

        model.objective = Objective(expr=model.pDiff, sense=minimize)
                
        solver = SolverFactory(solver_choice)
        # solver = SolverFactory('ipopt')
        result = solver.solve(model, tee=False)

        ### update battery SoC, return dispatch power
        if (result.solver.status == SolverStatus.ok) and (result.solver.termination_condition == TerminationCondition.optimal):
            self.SoC = model.SC.value
            self.HisSoC[future_time] = self.SoC
            return [model.pWR.value * self.PowerBase, 0]
        else:
            print("Solver Status: ", result.solver.status)
            ### if no solution, remove transmission loss and reserve from wind power for dispatch, no battery operation
            self.HisSoC[future_time] = self.SoC
            return [max(WP*(1-self.RatedPower/self.g/self.Vmax[0]**2), 0)*self.PowerBase, 0]
        

