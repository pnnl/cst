"""
CoSim Toolbox Simulations Package

This module provides a unified API for reading and writing co-simulation federates
"""

# Core data structures and class for HELICS
from .helicsConfig import (
    HelicsPubGroup,
    HelicsSubGroup,
    HelicsEndPtGroup,
    HelicsMsg,
    Collect,
)

# Factory functions for easy instantiation
from .federation import (
    FederateConfig,
    FederationConfig,
)

# Concrete Manager implementations
from .federate import Federate
from .dockerRunner import DockerRunner
from .federateLogger import FederateLogger

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
]