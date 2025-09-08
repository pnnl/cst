"""
CoSim Toolbox Data Management Module.

This module provides a unified API for reading and writing co-simulation
time-series data and metadata to various storage backends.

The primary entry points are the factory functions and the manager classes.

Example Usage:
    from cosim_toolbox.dbms import create_timeseries_manager, TSRecord

    # Create a CSV-based manager
    with create_timeseries_manager("csv", "/path/to/data", analysis_name="my_sim") as ts_manager:
        record = TSRecord(...)
        ts_manager.add_record(record)
"""

# Core data structures and abstract classes
from cosim_toolbox.dbms.abstractions import (
    TSRecord,
    TimeSeriesManager,
    MetadataManager,
)

# Factory functions for easy instantiation
from cosim_toolbox.dbms.factories import (
    create_timeseries_manager,
    create_metadata_manager,
)

# Concrete Manager implementations
from cosim_toolbox.dbms.json_metadata import JSONMetadataManager
from cosim_toolbox.dbms.mongo_metadata import MongoMetadataManager
from cosim_toolbox.dbms.csv_timeseries import CSVTimeSeriesManager
from cosim_toolbox.dbms.postgresql_timeseries import PostgreSQLTimeSeriesManager

# Public API definition
__all__ = [
    "TSRecord",
    "TimeSeriesManager",
    "MetadataManager",
    "create_timeseries_manager",
    "create_metadata_manager",
    "CSVTimeSeriesManager",
    "PostgreSQLTimeSeriesManager",
    "JSONMetadataManager",
    "MongoMetadataManager",
]