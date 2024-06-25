# EGRET Overview

## Sales Pitch 
Stealing from the [EGRET Githb page](https://github.com/grid-parity-exchange/Egret)...

"EGRET is a Python-based package for electrical grid optimization based on the Pyomo optimization
modeling language. EGRET is designed to be friendly for performing high-level analysis (e.g., as an
engine for solving different optimization formulations), while also providing flexibility for
researchers to rapidly explore new optimization formulations."

Major features:

* Expression and solution of unit commitment problems, including full ancillary service stack
* Expression and solution of economic dispatch (optimal power flow) problems (e.g, DCOPF, ACOPF)
* Library of different problem formulations and approximations
* Generic handling of data across model formulations
* Declarative model representation to support formulation development



## Similarity to MATPOWER

EGRET is similar to the well-established MATPOWER in that it is not a simulator, _per se_, but an optimization formulation library that is intended to make it easier to construct and solve common power system optimization problems. Both packages do not have support for advancing through simulated time. Both support external solvers to a greater or lesser extent. MATLAB has been developed and supported for close to three decades while EGRET is newer (around a decade old) but is built on Pyomo, a Python-based optimization library which also has a long development history. Both are open source.

## EGRET over MATPOWER

The decision to use EGRET over MATPOWER is largely linked to the support for external solvers and a desire to produce an open-source tool that is readily useable. MATPOWER is most often used in MATLAB though it does support the open-source clone of MATLAB, Octave. Based on our experience in previous projects we have realized that commercial solvers are often necessary to execute some of the optimization problems in a timely manner. Our experience has been that the external solver support in MATLAB is quite good but using it requires a MATLAB license which for some users is prohibitively expensive. Alternatively, though the MATPOWER does work in Octave and Octave is an open-source tool under active development and support, the external solver support in Ocrave is still lacking at this time.

EGRET is both an open-source tool and has excellent external solver support (as demonstrated by several recent and on-going projects around the DoE Lab complex). Additionally, with PNNL not being the only Lab interested in seeing EGRET continue, there is good reason to believe an informal consortium of EGRET users have motivation maintain and improve EGRET to keep it a going concern. EGRET also allows us to more easily develop new optimization problem formulations for future market mechanisms.

## EGRET as the Core of a Market Simulator
EGRET comes with both unit commitment and economic dispatch optimization problem formulations built-in and thus can serve as the mathematical core for a market simulator. But simulating market operations involves more than solving the optimization problem. The specific tasks we expect to tackle in this development effort are:

  * **Developing tooling to support model ingestion and translation** - EGRET has some support for some model formats (the MATPOWER .mpc is one) and additional model converters will likely be necessary. In particular, there is interest in supporting CIM.
  * **Developing a time-management process** - With no sense of simulation time, it will be up to the development team to develop the functionality and APIs to change the power system model state as simulation time advances so that the EGRET optimization core is performing its optimization on the power system as of the correct simulation time. This work will not only involve APIs to change the model state but also data management APIs to read in data defining the model system state.
  * **Adding optimization models related to energy storage** - The existing unit commitment and economic dispatch models do not well-account for energy storage devices (_e.g._ hydro, batteries). With hydro common in the WECC and batteries rising in importance in the power system in general, adequate models for these devices will be important for future market operations.
  * **Error handling** - EGRET does not guarantee it will find a solution to the optimization problems of a given power system state and developing appropriate responses to these failures will fall on the development team.
  * **Market protocol implementation** - Solving the optimization problem is the mathematical core around running a market but doing so is only one step in a larger protocol. This protocol involves steps such as collecting bids and distributing market-clearing results. Ideally the market protocols would be developed for a variety of market models (_e.g._ double-auction, order-book).
  * **HELICS integration** - To allow the tool to be used in larger HELICS-based analysis (such as TESP), the HELICS library and API calls will need to be worked into the main time-management system.

## References
Garcia, Manuel Joseph, Eldridge, Brent, Anya, Castillo, and Knueven, Ben. The EGRET Library Of Unit Commitment and Economic Dispatch Models and Methods For Large-scale Linear OPF.. United States: N. p., 2020. Web. doi:10.2172/1826439.

Knueven, Bernard, Watson, Jean-Paul. Reassessing the State-of-the-Art in Stochastic Unit Committment Solvers. 2020. https://www.ferc.gov/sites/default/files/2020-08/W3A-4_Kneuven.pdf

Knueven, Bernard. Transmission Constraint Screening for Production Cost Modeling at Scale. United States: N. p., 2022. Web.