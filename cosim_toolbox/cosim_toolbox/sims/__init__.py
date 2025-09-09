"""
CoSim Toolbox Simulations Package

This module provides a unified API for reading and writing co-simulation federates
"""

# Core data structures and class for HELICS
from cosim_toolbox.sims.helicsConfig import (
    HelicsPubGroup,
    HelicsSubGroup,
    HelicsEndPtGroup,
    HelicsMsg,
    Collect,
)

# Factory functions for easy instantiation
from cosim_toolbox.sims.federation import (
    FederateConfig,
    FederationConfig,
)

# Concrete Manager implementations
from cosim_toolbox.sims.federate import Federate
from cosim_toolbox.sims.dockerRunner import DockerRunner
from cosim_toolbox.sims.federateLogger import FederateLogger

# Deprecated apis
from cosim_toolbox.sims.dbConfigs import DBConfigs
from cosim_toolbox.sims.dbResults import DBResults
from cosim_toolbox.sims.readConfig import ReadConfig

# Public API definition
__all__ = [
    "Collect",
    "HelicsPubGroup",
    "HelicsSubGroup",
    "HelicsMsg",
    "FederateConfig",
    "FederationConfig",
    "Federate",
    "DockerRunner",
    "FederateLogger",
    "DBConfigs",
    "DBResults",
]