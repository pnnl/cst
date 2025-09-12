"""
Factory functions for creating data managers.

@author Nathan Gray
"""

# Use relative imports within the module
import cosim_toolbox as env
from .abstractions import TimeSeriesManager, MetadataManager


def create_timeseries_manager(
    backend: str = "postgres", analysis_name: str = "default", **kwargs
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
        from cosim_toolbox.dbms import CSVTimeSeriesManager

        # assign kwargs to backend option
        for key, value in kwargs.items():
            if key in env.csv_data_db:
                env.csv_data_db[key] = value
        return CSVTimeSeriesManager(**env.csv_data_db, analysis_name=analysis_name)
    elif backend == "postgres":
        from cosim_toolbox.dbms import PostgreSQLTimeSeriesManager

        # assign kwargs to backend option
        for key, value in kwargs.items():
            if key in env.pg_data_db:
                env.pg_data_db[key] = value
        return PostgreSQLTimeSeriesManager(
            **env.pg_data_db, analysis_name=analysis_name
        )
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
        from cosim_toolbox.dbms import JSONMetadataManager

        # assign kwargs to backend option
        for key, value in kwargs.items():
            if key in env.json_meta_db:
                env.json_meta_db[key] = value
        return JSONMetadataManager(**env.json_meta_db)

    elif backend == "mongo":
        from cosim_toolbox.dbms import MongoMetadataManager

        # assign kwargs to backend option
        for key, value in kwargs.items():
            if key in env.mongo_meta_db:
                env.mongo_meta_db[key] = value
        return MongoMetadataManager(**env.mongo_meta_db)

    else:
        raise ValueError(f"Unknown metadata backend: {backend}. Supported: json, mongo")
