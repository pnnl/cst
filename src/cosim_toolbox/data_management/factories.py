"""
Factory functions for creating data managers.

@author Nathan Gray
"""

# Use relative imports within the module
import cosim_toolbox as env
from data_management.abstractions import TimeSeriesManager, MetadataManager


def create_timeseries_manager(
    backend: str, analysis: str, **kwargs
) -> TimeSeriesManager:
    """
    Factory function to create appropriate time-series data manager.
    Args:
        backend (str): Backend type ("csv", "postgres").
        analysis (str): Analysis name.
        **kwargs: Backend-specific options.

    Returns:
        TimeSeriesManager: Manager for writing data with the specified backend
    """
    backend = backend.lower()
    if backend == "csv":
        from data_management.csv_timeseries import CSVTimeSeriesManager

        return CSVTimeSeriesManager(**env.csv_data_db, analysis_name=analysis)
    elif backend == "postgres":
        from data_management.postgresql_timeseries import PostgreSQLTimeSeriesManager

        return PostgreSQLTimeSeriesManager(**env.pg_data_db, analysis_name=analysis)
    else:
        raise ValueError(
            f"Unknown time-series backend: {backend}. Supported: csv, postgresql"
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
        from data_management.json_metadata import JSONMetadataManager

        # assign kwargs to backend option
        for key, value in kwargs.items():
            if key in env.json_meta_db:
                env.json_meta_db[key] = value
        return JSONMetadataManager(**env.json_meta_db)

    elif backend == "mongo":
        from data_management.mongo_metadata import MongoMetadataManager

        # assign kwargs to backend option
        for key, value in kwargs.items():
            if key in env.mongo_meta_db:
                env.mongo_meta_db[key] = value
        return MongoMetadataManager(**env.mongo_meta_db)

    else:
        raise ValueError(f"Unknown metadata backend: {backend}. Supported: json, mongo")
