"""
CoSim Toolbox Simulations Package

This module provides a unified API for reading and writing co-simulation federates
"""


# Concrete Manager implementations
from .docker_runner import DockerRunner
from .federate import Federate
from .federate_logger import FederateLogger

# Factory functions for easy instantiation
from .federation import (
    FederateConfig,
    FederationConfig,
)

# Core data structures and class for HELICS
from .helics_config import (
    Collect,
    HelicsEndPtGroup,
    HelicsMsg,
    HelicsPubGroup,
    HelicsSubGroup,
)

# Public API definition
__all__ = [
    "Collect",
    "DockerRunner",
    "Federate",
    "FederateConfig",
    "FederateLogger",
    "FederationConfig",
    "HelicsEndPtGroup",
    "HelicsMsg",
    "HelicsPubGroup",
    "HelicsSubGroup",
]