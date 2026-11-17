"""
Core data management abstractions for CoSim Toolbox.
Provides TSRecord dataclass.

@author Nathan Gray
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class TSRecord:
    real_time: datetime
    sim_time: float
    scenario: str
    federate: str
    data_name: str
    data_value: Any
    receiving_federate: str | None = None
    receiving_endpoint: str | None = None
    data_type: str | None = None  # "hdt_string", "hdt_endpoint", "hdt_double", etc.

    def __post_init__(self) -> None:
        # Auto-detect type if not provided
        if self.data_type is None:
            self.data_type = self._auto_detect_type()

    def _auto_detect_type(self) -> str:
        """Auto-detect data type from value"""

        if self.receiving_endpoint is not None or self.receiving_federate is not None:
            return "hdt_endpoint"
        elif isinstance(self.data_value, bool):
            return "hdt_boolean"
        elif isinstance(self.data_value, int):
            return "hdt_integer"
        elif isinstance(self.data_value, float):
            return "hdt_double"
        elif isinstance(self.data_value, complex):
            return "hdt_complex"
        elif isinstance(self.data_value, str):
            return "hdt_string"
        elif isinstance(self.data_value, (list, tuple)):
            return "hdt_vector"  # Could be enhanced for complex vectors
        return "hdt_string"  # Default fallback

    def json(self, func):
        if self.data_type == "hdt_endpoint":
            params = {
                'real_time': self.real_time,
                'sim_time': self.sim_time,
                'scenario': self.scenario,
                'federate': self.federate,
                'data_name': self.data_name,
                'receiving_federate': self.receiving_federate,
                'receiving_endpoint': self.receiving_endpoint,
                'data_value': func(self.data_value),
            }
        else:
            params = {
                'real_time': self.real_time,
                'sim_time': self.sim_time,
                'scenario': self.scenario,
                'federate': self.federate,
                'data_name': self.data_name,
                'data_value': func(self.data_value),
            }
        return params


