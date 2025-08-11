"""
PostgreSQL-based time-series data management for CoSim Toolbox.
Provides PostgreSQL storage for time-series data using TSRecord structure.
Uses composition-based approach with separate reader/writer classes.
@author: [AUTHOR]
"""

import logging
import pandas as pd
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import re

try:
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extras import execute_batch, RealDictCursor

    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

from .data_management import (
    TSDataWriter,
    TSDataReader,
    TSDataManager,
    TSRecord,
    ConnectionInfo,
)

logger = logging.getLogger(__name__)


class PostgreSQLTimeSeriesWriter(TSDataWriter):
    """
    PostgreSQL-based time-series data writer.
    Writes time-series data to PostgreSQL database using third-normal form structure.
    """

    # Map Python types to PostgreSQL data types and table suffixes
    TYPE_MAPPING = {
        float: ("hdt_double", "DOUBLE PRECISION"),
        int: ("hdt_integer", "BIGINT"),
        str: ("hdt_string", "TEXT"),
        bool: ("hdt_boolean", "BOOLEAN"),
        complex: ("hdt_complex", "TEXT"),  # Store as string representation
        list: ("hdt_vector", "TEXT"),  # Store as JSON string
        tuple: ("hdt_vector", "TEXT"),  # Store as JSON string
    }

    def __init__(self, connection_info: ConnectionInfo):
        """
        Initialize PostgreSQL time-series writer.
        Args:
            connection_info: Dict containing connection parameters
        """
        super().__init__(connection_info)
        if not PSYCOPG2_AVAILABLE:
            raise ImportError(
                "psycopg2 is required for PostgreSQL support. Install with: pip install psycopg2-binary"
            )

        self.host = connection_info["host"]
        self.port = connection_info["port"]
        self.database = connection_info["database"]
        self.user = connection_info["user"]
        self.password = connection_info["password"]
        self.schema_name = connection_info["schema_name"]
        self.batch_size = connection_info.get("batch_size", 1000)

        self.connection = None
        self._table_cache = set()  # Cache of created tables

    def _get_data_type_info(self, value: Any) -> tuple[str, str]:
        """
        Get data type information for a given value.
        Args:
            value: The data value to classify
        Returns:
            tuple: (table_suffix, postgres_type)
        """
        if isinstance(value, bool):  # Check bool before int
            return self.TYPE_MAPPING[bool]
        elif isinstance(value, int):
            return self.TYPE_MAPPING[int]
        elif isinstance(value, float):
            return self.TYPE_MAPPING[float]
        elif isinstance(value, complex):
            return self.TYPE_MAPPING[complex]
        elif isinstance(value, str):
            return self.TYPE_MAPPING[str]
        elif isinstance(value, (list, tuple)):
            return self.TYPE_MAPPING[list]
        else:
            # Default to string representation for unknown types
            return self.TYPE_MAPPING[str]

    def _format_value_for_postgres(self, value: Any) -> Any:
        """
        Format a value for PostgreSQL storage.
        Args:
            value: The value to format
        Returns:
            Formatted value suitable for PostgreSQL
        """
        if isinstance(value, (list, tuple)):
            import json

            return json.dumps(value)
        elif isinstance(value, complex):
            return str(value)
        elif isinstance(value, datetime):
            return value.isoformat()
        else:
            return value

    def _validate_schema_name(self, name: str) -> None:
        """Validate that a schema name is safe for PostgreSQL use."""
        if not name or len(name) > 63:  # PostgreSQL identifier limit
            raise ValueError(f"Schema name invalid (empty or >63 chars): {name}")

        # PostgreSQL identifier rules: start with letter/underscore, contain letters/digits/underscores
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
            raise ValueError(f"Schema name contains invalid characters: {name}")

        # Check for PostgreSQL reserved words (basic check)
        reserved = {
            "user",
            "table",
            "column",
            "index",
            "constraint",
            "database",
            "schema",
            "select",
            "insert",
            "update",
            "delete",
            "create",
            "drop",
            "alter",
        }
        if name.lower() in reserved:
            raise ValueError(f"Schema name is reserved: {name}")

    def connect(self) -> bool:
        """
        Establish connection to PostgreSQL database.
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            connection_params = {
                "host": self.host,
                "port": self.port,
                "database": self.database,
                "user": self.user,
                "password": self.password,
            }

            self.connection = psycopg2.connect(**connection_params)
            self.connection.autocommit = True  # Enable autocommit for DDL operations

            # Create database if it doesn't exist
            self._ensure_database_exists()

            # Create schema if it doesn't exist
            self._ensure_schema_exists()

            self._is_connected = True
            logger.info(
                f"PostgreSQL time-series writer connected to: {self.host}:{self.port}/{self.database}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            if self.connection:
                self.connection.close()
                self.connection = None
            return False

    def disconnect(self) -> None:
        """
        Close connection to PostgreSQL database.
        """
        if self.connection:
            self.connection.close()
            self.connection = None
        self._is_connected = False
        self._table_cache.clear()
        logger.debug("PostgreSQL time-series writer disconnected")

    def _ensure_database_exists(self) -> None:
        """Ensure the target database exists."""
        # This is handled by connecting to the specified database
        # In production, the database should already exist
        pass

    def _ensure_schema_exists(self) -> None:
        """Ensure the schema exists."""
        try:
            self._validate_schema_name(self.schema_name)

            with self.connection.cursor() as cursor:
                create_schema_query = sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
                    sql.Identifier(self.schema_name)
                )
                cursor.execute(create_schema_query)
                logger.debug(f"Ensured schema exists: {self.schema_name}")

        except Exception as e:
            logger.error(f"Failed to create schema {self.schema_name}: {e}")
            raise

    def _ensure_table_exists(self, table_suffix: str, postgres_type: str) -> None:
        """
        Ensure the table exists for a given data type.
        Args:
            table_suffix (str): Table suffix (e.g., 'hdt_double')
            postgres_type (str): PostgreSQL data type
        """
        table_key = f"{self.schema_name}.{table_suffix}"
        if table_key in self._table_cache:
            return

        try:
            with self.connection.cursor() as cursor:
                create_table_query = sql.SQL("""
                    CREATE TABLE IF NOT EXISTS {}.{} (
                        id SERIAL PRIMARY KEY,
                        real_time TIMESTAMP WITH TIME ZONE NOT NULL,
                        sim_time DOUBLE PRECISION NOT NULL,
                        scenario TEXT NOT NULL,
                        federate TEXT NOT NULL,
                        data_name TEXT NOT NULL,
                        data_value {} NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                """).format(
                    sql.Identifier(self.schema_name),
                    sql.Identifier(table_suffix),
                    sql.SQL(postgres_type),
                )
                cursor.execute(create_table_query)

                # Create indexes for better query performance
                self._create_table_indexes(table_suffix)

                self._table_cache.add(table_key)
                logger.debug(f"Ensured table exists: {table_key}")

        except Exception as e:
            logger.error(f"Failed to create table {table_key}: {e}")
            raise

    def _create_table_indexes(self, table_suffix: str) -> None:
        """Create indexes for better query performance."""
        try:
            with self.connection.cursor() as cursor:
                indexes = [
                    ("sim_time", "sim_time"),
                    ("scenario", "scenario"),
                    ("federate", "federate"),
                    ("data_name", "data_name"),
                    ("composite", "scenario, federate, data_name, sim_time"),
                ]

                for index_name, columns in indexes:
                    index_full_name = f"{table_suffix}_{index_name}_idx"
                    create_index_query = sql.SQL("""
                        CREATE INDEX IF NOT EXISTS {} ON {}.{} ({})
                    """).format(
                        sql.Identifier(index_full_name),
                        sql.Identifier(self.schema_name),
                        sql.Identifier(table_suffix),
                        sql.SQL(columns),
                    )
                    cursor.execute(create_index_query)

        except Exception as e:
            logger.warning(f"Failed to create indexes for {table_suffix}: {e}")

    def write_records(self, records: List[TSRecord]) -> bool:
        """
        Write TSRecord objects to PostgreSQL tables.
        Args:
            records (List[TSRecord]): List of time-series records to write
        Returns:
            bool: True if write successful, False otherwise
        """
        if not self._is_connected:
            logger.error("PostgreSQL writer not connected")
            return False

        if not records:
            return True

        try:
            # Group records by data type
            grouped_records = {}
            for record in records:
                table_suffix, postgres_type = self._get_data_type_info(
                    record.data_value
                )
                if table_suffix not in grouped_records:
                    grouped_records[table_suffix] = {
                        "postgres_type": postgres_type,
                        "records": [],
                    }
                grouped_records[table_suffix]["records"].append(record)

            # Write each group to its respective table
            for table_suffix, group_info in grouped_records.items():
                postgres_type = group_info["postgres_type"]
                group_records = group_info["records"]

                # Ensure table exists
                self._ensure_table_exists(table_suffix, postgres_type)

                # Prepare data for batch insert
                insert_data = []
                for record in group_records:
                    formatted_value = self._format_value_for_postgres(record.data_value)
                    insert_data.append(
                        (
                            record.real_time,
                            record.sim_time,
                            record.scenario,
                            record.federate,
                            record.data_name,
                            formatted_value,
                        )
                    )

                # Batch insert
                self._batch_insert(table_suffix, insert_data)

            logger.debug(f"Wrote {len(records)} records to PostgreSQL")
            return True

        except Exception as e:
            logger.error(f"Failed to write records to PostgreSQL: {e}")
            return False

    def _batch_insert(self, table_suffix: str, insert_data: List[tuple]) -> None:
        """
        Perform batch insert into PostgreSQL table.
        Args:
            table_suffix (str): Table suffix
            insert_data (List[tuple]): Data to insert
        """
        try:
            with self.connection.cursor() as cursor:
                insert_query = sql.SQL("""
                    INSERT INTO {}.{} (real_time, sim_time, scenario, federate, data_name, data_value)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """).format(
                    sql.Identifier(self.schema_name), sql.Identifier(table_suffix)
                )

                # Use execute_batch for better performance
                execute_batch(
                    cursor, insert_query, insert_data, page_size=self.batch_size
                )

        except Exception as e:
            logger.error(f"Failed to batch insert into {table_suffix}: {e}")
            raise

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


class PostgreSQLTimeSeriesReader(TSDataReader):
    """
    PostgreSQL-based time-series data reader.
    Reads time-series data from PostgreSQL database.
    """

    def __init__(self, connection_info: ConnectionInfo):
        """
        Initialize PostgreSQL time-series reader.
        Args:
            connection_info: Dict containing connection parameters
        """
        super().__init__(connection_info)
        if not PSYCOPG2_AVAILABLE:
            raise ImportError(
                "psycopg2 is required for PostgreSQL support. Install with: pip install psycopg2-binary"
            )

        self.host = connection_info["host"]
        self.port = connection_info["port"]
        self.database = connection_info["database"]
        self.user = connection_info["user"]
        self.password = connection_info["password"]
        self.schema_name = connection_info["schema_name"]

        self.connection = None

    def _parse_value_from_postgres(self, value: Any, table_suffix: str) -> Any:
        """
        Parse a value from PostgreSQL back to appropriate Python type.
        Args:
            value: Value from PostgreSQL
            table_suffix (str): Table suffix indicating data type
        Returns:
            Any: Parsed value in appropriate Python type
        """
        if table_suffix == "hdt_complex":
            return complex(value)
        elif table_suffix in ("hdt_vector", "hdt_complex_vector"):
            import json

            return json.loads(value)
        else:
            return value  # PostgreSQL handles basic types correctly

    def connect(self) -> bool:
        """
        Establish connection to PostgreSQL database.
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            connection_params = {
                "host": self.host,
                "port": self.port,
                "database": self.database,
                "user": self.user,
                "password": self.password,
            }

            self.connection = psycopg2.connect(**connection_params)
            self._is_connected = True
            logger.info(
                f"PostgreSQL time-series reader connected to: {self.host}:{self.port}/{self.database}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            if self.connection:
                self.connection.close()
                self.connection = None
            return False

    def disconnect(self) -> None:
        """
        Close connection to PostgreSQL database.
        """
        if self.connection:
            self.connection.close()
            self.connection = None
        self._is_connected = False
        logger.debug("PostgreSQL time-series reader disconnected")

    def read_data(
        self,
        start_time: Optional[float] = None,
        duration: Optional[float] = None,
        scenario_name: Optional[str] = None,
        federate_name: Optional[str] = None,
        data_name: Optional[str] = None,
        data_type: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Read time-series data from PostgreSQL database.
        Args:
            start_time (Optional[float]): Starting time for data query
            duration (Optional[float]): Duration in seconds for data query
            scenario_name (Optional[str]): Filter by scenario name
            federate_name (Optional[str]): Filter by federate name
            data_name (Optional[str]): Filter by data name
            data_type (Optional[str]): Filter by specific data type (table suffix)
        Returns:
            pd.DataFrame: Time-series data as a Pandas DataFrame
        """
        if not self._is_connected:
            logger.error("PostgreSQL reader not connected")
            return pd.DataFrame()

        try:
            # Get list of tables to query
            tables_to_query = self._get_tables_to_query(data_type)

            if not tables_to_query:
                logger.warning(f"No tables found in schema {self.schema_name}")
                return pd.DataFrame()

            all_data = []

            for table_suffix in tables_to_query:
                df = self._query_table(
                    table_suffix,
                    start_time=start_time,
                    duration=duration,
                    scenario_name=scenario_name,
                    federate_name=federate_name,
                    data_name=data_name,
                )
                if not df.empty:
                    # Parse data values back to proper types
                    df["data_value"] = df["data_value"].apply(
                        lambda x: self._parse_value_from_postgres(x, table_suffix)
                    )
                    all_data.append(df)

            if not all_data:
                return pd.DataFrame()

            # Combine all data
            combined_df = pd.concat(all_data, ignore_index=True)

            # Sort by simulation time
            if not combined_df.empty:
                combined_df = combined_df.sort_values("sim_time").reset_index(drop=True)

            logger.debug(f"Read {len(combined_df)} records from PostgreSQL")
            return combined_df

        except Exception as e:
            logger.error(f"Failed to read data from PostgreSQL: {e}")
            return pd.DataFrame()

    def _get_tables_to_query(self, data_type: Optional[str]) -> List[str]:
        """
        Get list of tables to query based on data_type filter.
        Args:
            data_type (Optional[str]): Specific data type to query
        Returns:
            List[str]: List of table names (suffixes)
        """
        try:
            with self.connection.cursor() as cursor:
                if data_type:
                    # Query specific table if it exists
                    cursor.execute(
                        """
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = %s AND table_name = %s
                    """,
                        (self.schema_name, data_type),
                    )
                    result = cursor.fetchone()
                    return [data_type] if result else []
                else:
                    # Query all time-series tables (those starting with 'hdt_')
                    cursor.execute(
                        """
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = %s AND table_name LIKE 'hdt_%'
                        ORDER BY table_name
                    """,
                        (self.schema_name,),
                    )
                    results = cursor.fetchall()
                    return [row[0] for row in results]

        except Exception as e:
            logger.error(f"Failed to get table list: {e}")
            return []

    def _query_table(
        self,
        table_suffix: str,
        start_time: Optional[float] = None,
        duration: Optional[float] = None,
        scenario_name: Optional[str] = None,
        federate_name: Optional[str] = None,
        data_name: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Query a specific table with filters.
        Args:
            table_suffix (str): Table suffix to query
            start_time, duration, scenario_name, federate_name, data_name: Filter parameters
        Returns:
            pd.DataFrame: Query results
        """
        try:
            # Build WHERE clause
            where_conditions = []
            params = []

            if scenario_name:
                where_conditions.append("scenario = %s")
                params.append(scenario_name)

            if federate_name:
                where_conditions.append("federate = %s")
                params.append(federate_name)

            if data_name:
                where_conditions.append("data_name = %s")
                params.append(data_name)

            if start_time is not None:
                where_conditions.append("sim_time >= %s")
                params.append(start_time)

            if duration is not None and start_time is not None:
                where_conditions.append("sim_time < %s")
                params.append(start_time + duration)
            elif duration is not None:
                where_conditions.append("sim_time < %s")
                params.append(duration)

            # Build query
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

            query = sql.SQL("""
                SELECT real_time, sim_time, scenario, federate, data_name, data_value
                FROM {}.{}
                WHERE {}
                ORDER BY sim_time, real_time
            """).format(
                sql.Identifier(self.schema_name),
                sql.Identifier(table_suffix),
                sql.SQL(where_clause),
            )

            # Execute query and return as DataFrame
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                results = cursor.fetchall()

                if not results:
                    return pd.DataFrame()

                # Convert to DataFrame
                df = pd.DataFrame(results)

                # Convert real_time to datetime if it's not already
                if "real_time" in df.columns:
                    df["real_time"] = pd.to_datetime(df["real_time"])

                return df

        except Exception as e:
            logger.error(f"Failed to query table {table_suffix}: {e}")
            return pd.DataFrame()

    # Utility methods
    def list_scenarios(self) -> List[str]:
        """
        Get list of unique scenarios in the database.
        Returns:
            List[str]: List of scenario names
        """
        if not self._is_connected:
            return []

        try:
            tables = self._get_tables_to_query(None)
            if not tables:
                return []

            scenarios = set()
            for table_suffix in tables:
                with self.connection.cursor() as cursor:
                    query = sql.SQL("SELECT DISTINCT scenario FROM {}.{}").format(
                        sql.Identifier(self.schema_name), sql.Identifier(table_suffix)
                    )
                    cursor.execute(query)
                    results = cursor.fetchall()
                    scenarios.update(row[0] for row in results)

            return sorted(list(scenarios))

        except Exception as e:
            logger.error(f"Failed to list scenarios: {e}")
            return []

    def list_federates(self) -> List[str]:
        """
        Get list of unique federates in the database.
        Returns:
            List[str]: List of federate names
        """
        if not self._is_connected:
            return []

        try:
            tables = self._get_tables_to_query(None)
            if not tables:
                return []

            federates = set()
            for table_suffix in tables:
                with self.connection.cursor() as cursor:
                    query = sql.SQL("SELECT DISTINCT federate FROM {}.{}").format(
                        sql.Identifier(self.schema_name), sql.Identifier(table_suffix)
                    )
                    cursor.execute(query)
                    results = cursor.fetchall()
                    federates.update(row[0] for row in results)

            return sorted(list(federates))

        except Exception as e:
            logger.error(f"Failed to list federates: {e}")
            return []

    def list_data_types(self) -> List[str]:
        """
        Get list of available data types (table suffixes).
        Returns:
            List[str]: List of data type names
        """
        return self._get_tables_to_query(None)

    def get_time_range(
        self, scenario_name: Optional[str] = None, federate_name: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Get the time range (min and max simulation times) for the data.
        Args:
            scenario_name (Optional[str]): Filter by scenario
            federate_name (Optional[str]): Filter by federate
        Returns:
            Dict[str, float]: Dictionary with 'min_time' and 'max_time' keys
        """
        if not self._is_connected:
            return {"min_time": 0.0, "max_time": 0.0}

        try:
            tables = self._get_tables_to_query(None)
            if not tables:
                return {"min_time": 0.0, "max_time": 0.0}

            min_times = []
            max_times = []

            for table_suffix in tables:
                where_conditions = []
                params = []

                if scenario_name:
                    where_conditions.append("scenario = %s")
                    params.append(scenario_name)

                if federate_name:
                    where_conditions.append("federate = %s")
                    params.append(federate_name)

                where_clause = (
                    " AND ".join(where_conditions) if where_conditions else "1=1"
                )

                with self.connection.cursor() as cursor:
                    query = sql.SQL("""
                        SELECT MIN(sim_time) as min_time, MAX(sim_time) as max_time
                        FROM {}.{}
                        WHERE {}
                    """).format(
                        sql.Identifier(self.schema_name),
                        sql.Identifier(table_suffix),
                        sql.SQL(where_clause),
                    )
                    cursor.execute(query, params)
                    result = cursor.fetchone()

                    if result and result[0] is not None:
                        min_times.append(result[0])
                        max_times.append(result[1])

            if not min_times:
                return {"min_time": 0.0, "max_time": 0.0}

            return {
                "min_time": float(min(min_times)),
                "max_time": float(max(max_times)),
            }

        except Exception as e:
            logger.error(f"Failed to get time range: {e}")
            return {"min_time": 0.0, "max_time": 0.0}

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


class PostgreSQLTimeSeriesManager(TSDataManager):
    """
    Joint PostgreSQL time-series manager using composition.
    Combines separate reader and writer instances that share a common connection.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "cst",
        user: str = "postgres",
        password: str = "",
        schema_name: str = "public",
        **kwargs,
    ):
        """
        Initialize PostgreSQL time-series manager.
        Args:
            host (str): PostgreSQL host
            port (int): PostgreSQL port
            database (str): Database name
            user (str): Username
            password (str): Password
            schema_name (str): Schema name (acts as analysis identifier)
            **kwargs: Additional connection parameters
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.schema_name = schema_name

        # Create location string for parent class
        location = f"postgresql://{user}@{host}:{port}/{database}"

        super().__init__(
            location,
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            schema_name=schema_name,
            **kwargs,
        )

    def _create_connection_info(self, location: str, **kwargs) -> ConnectionInfo:
        """Create shared connection info for PostgreSQL storage."""
        return {
            "host": kwargs.get("host", "localhost"),
            "port": kwargs.get("port", 5432),
            "database": kwargs.get("database", "cst"),
            "user": kwargs.get("user", "postgres"),
            "password": kwargs.get("password", ""),
            "schema_name": kwargs.get("schema_name", "public"),
            "batch_size": kwargs.get("batch_size", 1000),
        }

    def _create_writer(self, connection_info: ConnectionInfo) -> TSDataWriter:
        """Create PostgreSQL writer with shared connection info."""
        return PostgreSQLTimeSeriesWriter(connection_info)

    def _create_reader(self, connection_info: ConnectionInfo) -> TSDataReader:
        """Create PostgreSQL reader with shared connection info."""
        return PostgreSQLTimeSeriesReader(connection_info)

    # Expose utility methods from reader
    def list_scenarios(self) -> List[str]:
        """List available scenarios in the database."""
        return self.reader.list_scenarios()

    def list_federates(self) -> List[str]:
        """List available federates in the database."""
        return self.reader.list_federates()

    def list_data_types(self) -> List[str]:
        """List available data types in the database."""
        return self.reader.list_data_types()

    def get_time_range(
        self, scenario_name: Optional[str] = None, federate_name: Optional[str] = None
    ) -> Dict[str, float]:
        """Get the time range for the data."""
        return self.reader.get_time_range(scenario_name, federate_name)

    def delete_scenario_data(self, scenario_name: str) -> bool:
        """
        Delete all data for a specific scenario.
        Args:
            scenario_name (str): Name of the scenario to delete
        Returns:
            bool: True if deletion successful, False otherwise
        """
        if not self._is_connected:
            logger.error("PostgreSQL manager not connected")
            return False

        try:
            tables = self.reader._get_tables_to_query(None)

            for table_suffix in tables:
                with self.writer.connection.cursor() as cursor:
                    delete_query = sql.SQL(
                        "DELETE FROM {}.{} WHERE scenario = %s"
                    ).format(
                        sql.Identifier(self.schema_name), sql.Identifier(table_suffix)
                    )
                    cursor.execute(delete_query, (scenario_name,))

            logger.debug(f"Deleted scenario data: {scenario_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete scenario data: {e}")
            return False

    def delete_federate_data(self, federate_name: str) -> bool:
        """
        Delete all data for a specific federate.
        Args:
            federate_name (str): Name of the federate to delete
        Returns:
            bool: True if deletion successful, False otherwise
        """
        if not self._is_connected:
            logger.error("PostgreSQL manager not connected")
            return False

        try:
            tables = self.reader._get_tables_to_query(None)

            for table_suffix in tables:
                with self.writer.connection.cursor() as cursor:
                    delete_query = sql.SQL(
                        "DELETE FROM {}.{} WHERE federate = %s"
                    ).format(
                        sql.Identifier(self.schema_name), sql.Identifier(table_suffix)
                    )
                    cursor.execute(delete_query, (federate_name,))

            logger.debug(f"Deleted federate data: {federate_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete federate data: {e}")
            return False

    def delete_data_type(self, data_type: str) -> bool:
        """
        Delete all data for a specific data type (drop table).
        Args:
            data_type (str): Data type (table suffix) to delete
        Returns:
            bool: True if deletion successful, False otherwise
        """
        if not self._is_connected:
            logger.error("PostgreSQL manager not connected")
            return False

        try:
            with self.writer.connection.cursor() as cursor:
                drop_query = sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
                    sql.Identifier(self.schema_name), sql.Identifier(data_type)
                )
                cursor.execute(drop_query)

            # Remove from cache if present
            table_key = f"{self.schema_name}.{data_type}"
            self.writer._table_cache.discard(table_key)

            logger.debug(f"Deleted data type table: {data_type}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete data type {data_type}: {e}")
            return False

    def optimize_tables(self) -> bool:
        """
        Run VACUUM and ANALYZE on all tables for performance optimization.
        Returns:
            bool: True if optimization successful, False otherwise
        """
        if not self._is_connected:
            logger.error("PostgreSQL manager not connected")
            return False

        try:
            tables = self.reader._get_tables_to_query(None)

            # Need to disable autocommit for VACUUM
            original_autocommit = self.writer.connection.autocommit
            self.writer.connection.autocommit = False

            try:
                for table_suffix in tables:
                    with self.writer.connection.cursor() as cursor:
                        # VACUUM and ANALYZE
                        table_name = f"{self.schema_name}.{table_suffix}"
                        cursor.execute(f"VACUUM ANALYZE {table_name}")

                self.writer.connection.commit()
                logger.info(f"Optimized {len(tables)} tables")
                return True

            finally:
                self.writer.connection.autocommit = original_autocommit

        except Exception as e:
            logger.error(f"Failed to optimize tables: {e}")
            return False

    @property
    def schema_name(self) -> str:
        """Get the schema name."""
        return self._schema_name

    @schema_name.setter
    def schema_name(self, value: str) -> None:
        """Set the schema name and update connection info."""
        self._schema_name = value
        if hasattr(self, "connection_info"):
            self.connection_info["schema_name"] = value
            # Update reader and writer schema names
            if hasattr(self, "writer"):
                self.writer.schema_name = value
            if hasattr(self, "reader"):
                self.reader.schema_name = value
