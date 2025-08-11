"""
Factory for creating time-series data managers.
"""

from typing import Any
from .data_management import TSDataManager


def create_timeseries_manager(backend: str, location: str, **kwargs) -> TSDataManager:
    """
    Factory function to create appropriate time-series data manager.

    Args:
        backend (str): Backend type ("csv")
        location (str): Storage location (path for CSV)
        **kwargs: Backend-specific options
            - analysis_name (str): Analysis name for CSV (default: "default")

    Returns:
        TSDataManager: Configured time-series data manager

    Raises:
        ValueError: If backend is not supported
        ImportError: If required dependencies are missing
    """
    backend = backend.lower()

    if backend == "csv":
        from .csv_timeseries import CSVTimeSeriesManager

        analysis_name = kwargs.get("analysis_name", "default")
        return CSVTimeSeriesManager(location, analysis_name)
    else:
        raise ValueError(f"Unknown backend: {backend}. Supported: csv")


# Convenience functions
def create_csv_manager(
    location: str, analysis_name: str = "default"
) -> "CSVTimeSeriesManager":
    """Create CSV time-series manager."""
    return create_timeseries_manager("csv", location, analysis_name=analysis_name)
