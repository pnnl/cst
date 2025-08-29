"""
Factory for creating time-series data managers.
Updated to include PostgreSQL support.
"""

from typing import Any
from data_management import TimeSeriesManager


def create_timeseries_manager(
    backend: str, location: str, **kwargs
) -> TimeSeriesManager:
    """
    Factory function to create appropriate time-series data manager.

    Args:
        backend (str): Backend type ("csv", "postgresql")
        location (str): Storage location (path for CSV, connection string for PostgreSQL)
        **kwargs: Backend-specific options
            CSV options:
                - analysis_name (str): Analysis name for CSV (default: "default")
            PostgreSQL options:
                - location (str): PostgreSQL host (default: "localhost")
                - port (int): PostgreSQL port (default: 5432)
                - database (str): Database name (default: "cst")
                - user (str): Username (default: "postgres")
                - password (str): Password (default: "")
                - schema_name (str): Schema name (default: "public")
                - batch_size (int): Batch size for inserts (default: 1000)

    Returns:
        TSDataManager: Configured time-series data manager

    Raises:
        ValueError: If backend is not supported
        ImportError: If required dependencies are missing
    """
    backend = backend.lower()

    if backend == "csv":
        from data_management.csv_timeseries import CSVTimeSeriesManager

        analysis_name = kwargs.get("analysis_name", "default")
        return CSVTimeSeriesManager(location=location, analysis_name=analysis_name)
    elif backend in ("postgresql", "postgres"):
        from data_management.postgresql_timeseries import PostgreSQLTimeSeriesManager

        # Parse connection string or use individual parameters
        if location.startswith("postgresql://"):
            # Parse connection string: postgresql://user:password@host:port/database
            import re

            match = re.match(
                r"postgresql://(?:([^:]+)(?::([^@]+))?@)?([^:/]+)(?::(\d+))?/(.+)",
                location,
            )
            if match:
                user, password, host, port, database = match.groups()
                return PostgreSQLTimeSeriesManager(
                    location=host or "localhost",
                    port=int(port) if port else 5432,
                    database=database,
                    user=user or "postgres",
                    password=password or "",
                    analysis_name=kwargs.get("schema_name", "public"),
                )
            else:
                raise ValueError(f"Invalid PostgreSQL connection string: {location}")
        else:
            # Use location as host and get other parameters from kwargs
            return PostgreSQLTimeSeriesManager(
                location=location,
                port=kwargs.get("port", 5432),
                database=kwargs.get("database", "cst"),
                user=kwargs.get("user", "postgres"),
                password=kwargs.get("password", ""),
                analysis_name=kwargs.get("schema_name", "public"),
            )
    else:
        raise ValueError(f"Unknown backend: {backend}. Supported: csv, postgresql")
