"""
Factory functions for creating data managers.
"""
from typing import Any

# Use relative imports within the module
from .abstractions import TimeSeriesManager, MetadataManager

def create_timeseries_manager(backend: str, location: str, **kwargs) -> TimeSeriesManager:
    """
    Factory function to create appropriate time-series data manager.
    Args:
        backend (str): Backend type ("csv", "postgresql").
        location (str): Storage location (path for CSV, host for PostgreSQL).
        **kwargs: Backend-specific options.
    """
    backend = backend.lower()
    if backend == "csv":
        from .csv_timeseries import CSVTimeSeriesManager
        return CSVTimeSeriesManager(location, **kwargs)
    elif backend in ("postgresql", "postgres"):
        from .postgresql_timeseries import PostgreSQLTimeSeriesManager
        return PostgreSQLTimeSeriesManager(host=location, **kwargs)
    else:
        raise ValueError(f"Unknown time-series backend: {backend}. Supported: csv, postgresql")


def create_metadata_manager(backend: str, location: str, **kwargs) -> MetadataManager:
    """
    Factory function to create appropriate metadata manager.
    Args:
        backend (str): Backend type ("json", "mongo").
        location (str): Storage location (path for JSON, URI for MongoDB).
        **kwargs: Backend-specific options.
    """
    backend = backend.lower()
    if backend == "json":
        from .json_metadata import JSONMetadataManager
        return JSONMetadataManager(location=location, **kwargs)
    elif backend in ("mongo", "mongodb"):
        from .mongo_metadata import MongoMetadataManager
        return MongoMetadataManager(uri=location, **kwargs)
    else:
        raise ValueError(f"Unknown metadata backend: {backend}. Supported: json, mongo")