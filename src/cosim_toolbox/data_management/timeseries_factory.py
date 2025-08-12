"""
Factory for creating time-series data managers.
Updated to include PostgreSQL support.
"""

from typing import Any
from .data_management import TSDataManager


def create_timeseries_manager(backend: str, location: str, **kwargs) -> TSDataManager:
    """
    Factory function to create appropriate time-series data manager.

    Args:
        backend (str): Backend type ("csv", "postgresql")
        location (str): Storage location (path for CSV, connection string for PostgreSQL)
        **kwargs: Backend-specific options
            CSV options:
                - analysis_name (str): Analysis name for CSV (default: "default")
            PostgreSQL options:
                - host (str): PostgreSQL host (default: "localhost")
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
        from .csv_timeseries import CSVTimeSeriesManager

        analysis_name = kwargs.get("analysis_name", "default")
        return CSVTimeSeriesManager(location, analysis_name)
    elif backend in ("postgresql", "postgres"):
        from .postgresql_timeseries import PostgreSQLTimeSeriesManager

        # Parse connection string or use individual parameters
        if location.startswith("postgresql://"):
            # Parse connection string: postgresql://user:password@host:port/database
            import re
            match = re.match(
                r"postgresql://(?:([^:]+)(?::([^@]+))?@)?([^:/]+)(?::(\d+))?/(.+)",
                location
            )
            if match:
                user, password, host, port, database = match.groups()
                return PostgreSQLTimeSeriesManager(
                    host=host or "localhost",
                    port=int(port) if port else 5432,
                    database=database,
                    user=user or "postgres",
                    password=password or "",
                )
            else:
                raise ValueError(f"Invalid PostgreSQL connection string: {location}")
        else:
            # Use location as host and get other parameters from kwargs
            return PostgreSQLTimeSeriesManager(
                host=location,
                port=kwargs.get("port", 5432),
                database=kwargs.get("database", "cst"),
                user=kwargs.get("user", "postgres"),
                password=kwargs.get("password", ""),
                schema_name=kwargs.get("schema_name", "public"),
            )
    else:
        raise ValueError(f"Unknown backend: {backend}. Supported: csv, postgresql")


# Convenience functions
def create_csv_manager(
    location: str, analysis_name: str = "default"
) -> "CSVTimeSeriesManager":
    """Create CSV time-series manager."""
    return create_timeseries_manager("csv", location, analysis_name=analysis_name)


def create_postgresql_manager(
    host: str = "localhost",
    port: int = 5432,
    database: str = "cst",
    user: str = "postgres",
    password: str = "",
    schema_name: str = "public",
    **kwargs
) -> "PostgreSQLTimeSeriesManager":
    """Create PostgreSQL time-series manager."""
    return create_timeseries_manager(
        "postgresql", 
        host,
        port=port,
        database=database,
        user=user,
        password=password,
        schema_name=schema_name,
        **kwargs
    )


def create_postgresql_manager_from_url(url: str, **kwargs) -> "PostgreSQLTimeSeriesManager":
    """Create PostgreSQL time-series manager from connection URL."""
    return create_timeseries_manager("postgresql", url, **kwargs)