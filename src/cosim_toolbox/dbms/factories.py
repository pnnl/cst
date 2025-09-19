"""
Factory functions for creating data managers.

@author Nathan Gray
"""

# Use relative imports within the module
from .. import csv_data_db, pg_data_db, json_meta_db, mongo_meta_db
from .abstractions import TimeSeriesManager, MetadataManager


def create_timeseries_manager(
        backend: str = "postgres", analysis_name: str = "default", **kwargs
) -> TimeSeriesManager:
    """
    Factory function to create appropriate time-series data manager.
    Args:
        backend (str): Backend type ("csv", "postgres").
        analysis_name (str): Analysis name.
        **kwargs: Backend-specific options.

    Returns:
        TimeSeriesManager: Manager for writing data with the specified backend
    """
    backend = backend.lower()
    if backend == "csv":
        from . import CSVTimeSeriesManager

        # assign kwargs to backend option
        for key, value in kwargs.items():
            if key in csv_data_db:
                csv_data_db[key] = value
        return CSVTimeSeriesManager(analysis_name=analysis_name, **csv_data_db)
    elif backend == "postgres":
        from . import PostgreSQLTimeSeriesManager

        # assign kwargs to backend option
        for key, value in kwargs.items():
            if key in pg_data_db:
                pg_data_db[key] = value
        return PostgreSQLTimeSeriesManager(analysis_name=analysis_name, **pg_data_db)
    else:
        raise ValueError(
            f"Unknown time-series backend: {backend}. Supported: csv, postgres"
        )


def create_metadata_manager(backend: str = "mongo", **kwargs) -> MetadataManager:
    """
    Factory function to create appropriate metadata manager.
    Args:
        backend (str): Backend type ("json", "mongo").
        **kwargs: Backend-specific options.

    Returns:
        MetadataManger: Manager for writing data with the specified backend
    """

    backend = backend.lower()
    if backend == "json":
        from . import JSONMetadataManager

        # assign kwargs to backend option
        for key, value in kwargs.items():
            if key in json_meta_db:
                json_meta_db[key] = value
        return JSONMetadataManager(**json_meta_db)

    elif backend == "mongo":
        from . import MongoMetadataManager

        # assign kwargs to backend option
        for key, value in kwargs.items():
            if key in mongo_meta_db:
                mongo_meta_db[key] = value
        return MongoMetadataManager(**mongo_meta_db)

    else:
        raise ValueError(f"Unknown metadata backend: {backend}. Supported: json, mongo")
