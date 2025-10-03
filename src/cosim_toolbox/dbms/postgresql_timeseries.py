"""
PostgreSQL-based time-series data management for CoSim Toolbox.
Refactored to use a composition-based architecture for clarity,
testability, and maintainability.

@author Nathan Gray
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import psycopg2

try:
    from psycopg2 import sql
    from psycopg2.extras import RealDictCursor, execute_values

    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

from .abstractions import (
    TSDataReader,
    TSDataManager,
    TSDataWriter,
    TSRecord,
)
from .validation import ValidationError, validate_database_identifier

logger = logging.getLogger(__name__)

type_mapping = {
    "hdt_string": "TEXT",
    "hdt_double": "DOUBLE PRECISION",
    "hdt_integer": "BIGINT",
    "hdt_complex": "VARCHAR(255)",
    "hdt_vector": "TEXT",
    "hdt_complex_vector": "TEXT",
    "hdt_named_point": "VARCHAR(255)",
    "hdt_boolean": "BOOLEAN",
    "hdt_time": "TIMESTAMP",
    "hdt_json": "TEXT",
    "hdt_endpoint": "TEXT",
}


class _PostgresConnectionHelper:
    """Manages the connection and common logic for PostgreSQL."""

    def __init__(
        self,
        location: str,
        port: int,
        database: str,
        user: str,
        password: str,
        analysis_name: str,
        use_timescale: bool = False,
    ):
        if not PSYCOPG2_AVAILABLE:
            raise ImportError(
                "psycopg2 is required for PostgreSQL support. Install with: pip install psycopg2-binary"
            )

        self.conn_params = {
            "host": location,
            "port": port,
            "database": database,
            "user": user,
            "password": password,
        }
        self.analysis_name = analysis_name
        self.use_timescale = use_timescale
        self.connection: Optional[psycopg2.extensions.connection] = None

    def connect(self) -> bool:
        """Establishes and validates the PostgreSQL connection.

        Returns:
            bool: Flag indicating success of connection to PostgreSQL
        """
        if self.connection and not self.connection.closed:
            return True
        try:
            validate_database_identifier(self.analysis_name, "analysis")
            self.connection = psycopg2.connect(
                host=self.conn_params["host"],
                port=self.conn_params["port"],
                database=self.conn_params["database"],
                user=self.conn_params["user"],
                password=self.conn_params["password"],
            )
            self.connection.autocommit = False
            self._ensure_analysis_exists()
            logger.info(
                f"PostgreSQL helper connected to: {self.conn_params['host']}/{self.conn_params['database']}"
            )
            return True
        except (ValidationError, psycopg2.Error) as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            self.connection = None
            return False

    def disconnect(self) -> None:
        """Closes the PostgreSQL connection.

        Returns:
            None
        """
        if self.connection and not self.connection.closed:
            self.connection.close()
            logger.debug("PostgreSQL helper disconnected.")
        self.connection = None

    def _ensure_analysis_exists(self) -> None:
        """Checks to see if schema exists in current PostgreSQL database

        Returns:
            None
        """
        assert self.connection is not None, "Database not connected"
        with self.connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
                    sql.Identifier(self.analysis_name)
                )
            )
        self.connection.commit()

    def _ensure_endpoint_table_exists(self) -> None:
        """Create endpoint-specific table structure."""
        assert self.connection is not None, "Database not connected"
        with self.connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("""
                CREATE TABLE IF NOT EXISTS {analysis}.endpoints (
                    id SERIAL PRIMARY KEY,
                    real_time TIMESTAMPTZ NOT NULL,
                    sim_time DOUBLE PRECISION NOT NULL,
                    scenario TEXT NOT NULL,
                    federate TEXT NOT NULL,
                    data_name TEXT NOT NULL,
                    receiving_federate TEXT NOT NULL,
                    receiving_endpoint TEXT NOT NULL,
                    data_value TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                )""").format(analysis=sql.Identifier(self.analysis_name))
            )

            # Add indexes
            for col in [
                "sim_time",
                "scenario",
                "federate",
                "receiving_federate",
            ]:
                idx_name = sql.Identifier(f"idx_endpoints_{col}")
                cursor.execute(
                    sql.SQL(
                        "CREATE INDEX IF NOT EXISTS {idx} ON {analysis}.endpoints ({col})"
                    ).format(
                        idx=idx_name,
                        analysis=sql.Identifier(self.analysis_name),
                        col=sql.Identifier(col),
                    )
                )
        self.connection.commit()

    @staticmethod
    def get_data_type_info(record: TSRecord) -> Tuple[str, str]:
        """
        Get table name and PostgreSQL column type from TSRecord.

        Args:
            record (TSRecord): The record containing data_type and data_value

        Returns:
            Tuple[str, str]: (table_suffix, postgres_column_type)
        """
        # If data_type is explicitly set, use it
        table_name = record.data_type.lower()
        postgres_type = type_mapping.get(table_name, "TEXT")
        return table_name, postgres_type

    @staticmethod
    def format_value_for_db(value: Any) -> Any:
        """Formats passed in value for writing to PostgreSQL

        Args:
            value (Any): value to be formatted

        Returns:
            Any: Formatted data for PostgreSQL
        """
        if isinstance(value, (list, tuple)):
            return json.dumps(value)
        if isinstance(value, complex):
            return str(value)
        return value

    @staticmethod
    def parse_value_from_db(value: Any, table_suffix: str) -> Any:
        """Formats read data from PostgreSQL into Python data types

        Only used to handle "hdt_complex", "hdt_vector", "hdt_complex_vector".

        Args:
            value (Any): Data read from PostgreSQL database
            table_suffix (str): CST data type of data

        Returns:
            Any: Formatted data
        """
        if value is None:
            return None
        if table_suffix == "hdt_complex":
            return complex(value)
        if table_suffix in ("hdt_vector", "hdt_complex_vector"):
            return json.loads(value)
        return value


class PostgreSQLTimeSeriesWriter(TSDataWriter):
    """PostgreSQL-based time-series data writer."""

    def __init__(
        self,
        *,  # Everything must be keyword
        location: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        analysis_name: Optional[str] = None,
        use_timescale: bool = False,
        batch_size: int = 1000,
        helper: Optional[_PostgresConnectionHelper] = None,
    ):
        super().__init__()
        self.batch_size = batch_size
        self._table_cache: set = set()
        self.helper: _PostgresConnectionHelper
        if helper:
            self.helper = helper
            self._owns_connection = False
        elif (
            location is not None
            and port is not None
            and database is not None
            and user is not None
            and password is not None
            and analysis_name is not None
        ):
            self.helper = _PostgresConnectionHelper(
                location, port, database, user, password, analysis_name, use_timescale
            )
            self._owns_connection = True
        else:
            raise ValueError(
                "Must provide either a 'helper' or all connection parameters (host, port, etc.)."
            )

    def connect(self) -> bool:
        """Establishes connection to the PostgreSQL server.

        Returns:
            bool: Flag indicating success of connection to MongoDB
        """
        if self._owns_connection:
            if not self.helper.connect():
                return False
        if self.helper.connection and not self.helper.connection.closed:
            self._is_connected = True
            return True
        logger.error(
            "PostgreSQL writer cannot connect; the connection helper is disconnected."
        )
        return False

    def disconnect(self) -> None:
        """Closes the connection to the PostgreSQL server.

        Returns:
            None
        """
        if self._owns_connection:
            self.helper.disconnect()
        self._is_connected = False
        self._table_cache.clear()

    def _ensure_table_exists(self, table_name: str) -> None:
        """Checks to see specified PostgreSQL table exists

        Args:
            table_name (str): Name of table whose existance is
            being checked

        Returns:
            None
        """
        table_key = f"{self.helper.analysis_name}.{table_name}"
        if table_key in self._table_cache:
            return
        assert self.helper.connection is not None, "Database not connected"
        with self.helper.connection.cursor() as cursor:
            if table_name == "hdt_endpoint":
                cursor.execute(
                    sql.SQL("""
                    CREATE TABLE IF NOT EXISTS {analysis}.{table} (
                        id SERIAL PRIMARY KEY, 
                        real_time TIMESTAMPTZ NOT NULL, 
                        sim_time DOUBLE PRECISION NOT NULL,
                        scenario TEXT NOT NULL, 
                        federate TEXT NOT NULL, 
                        data_name TEXT NOT NULL,
                        receiving_federate TEXT,
                        receiving_endpoint TEXT,
                        data_value TEXT NOT NULL, 
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )""").format(
                        analysis=sql.Identifier(self.helper.analysis_name),
                        table=sql.Identifier(table_name),
                    )
                )
            else:
                cursor.execute(
                    sql.SQL("""
                    CREATE TABLE IF NOT EXISTS {analysis}.{table} (
                        id SERIAL PRIMARY KEY, 
                        real_time TIMESTAMPTZ NOT NULL, 
                        sim_time DOUBLE PRECISION NOT NULL,
                        scenario TEXT NOT NULL, 
                        federate TEXT NOT NULL, 
                        data_name TEXT NOT NULL,
                        data_value {pg_type} NOT NULL, 
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )""").format(
                        analysis=sql.Identifier(self.helper.analysis_name),
                        table=sql.Identifier(table_name),
                        pg_type=sql.SQL(type_mapping[table_name]),
                    )
                )
            if self.helper.use_timescale:
                try:
                    full_table_name = f"{self.helper.analysis_name}.{table_name}"
                    cursor.execute(
                        "SELECT 1 FROM timescaledb_information.hypertables WHERE hypertable_schema = %s AND hypertable_name = %s",
                        (self.helper.analysis_name, table_name),
                    )
                    if cursor.fetchone() is None:
                        logger.info(f"Creating hypertable for {full_table_name}")
                        cursor.execute(
                            sql.SQL(
                                f"SELECT create_hypertable({full_table_name}, 'real_time')"
                            ),
                        )
                except psycopg2.Error as ts_error:
                    logger.warning(
                        f"Could not create hypertable for {table_key}. Is TimescaleDB enabled? Error: {ts_error}"
                    )
                    self.helper.connection.rollback()
            else:  # if not using timescale
                # TODO: experiment with best use of indexes; may add overhead on write
                for col in ["sim_time", "scenario", "federate", "data_name"]:
                    idx_name = sql.Identifier(f"idx_{table_name}_{col}")
                    cursor.execute(
                        sql.SQL(
                            "CREATE INDEX IF NOT EXISTS {idx} ON {analysis}.{table} ({col})"
                        ).format(
                            idx=idx_name,
                            analysis=sql.Identifier(self.helper.analysis_name),
                            table=sql.Identifier(table_name),
                            col=sql.Identifier(col),
                        )
                    )
        self.helper.connection.commit()
        self._table_cache.add(table_key)

    def write_records(self, records: List[TSRecord]) -> bool:
        """Writes records (rows) to PostgreSQL database

        Args:
            records (List[TSRecord]): data to be written to database

        Returns:
            bool: Flag indicating data was successfully written to
                PostgreSQL database.
        """
        if not self._is_connected:
            logger.error("PostgreSQL writer not connected.")
            return False
        assert self.helper.connection is not None, "Database not connected"
        if not records:
            return True
        try:
            grouped_records: Dict[str, List[tuple]] = {}
            for record in records:
                table_name = str(record.data_type)
                data_tuple: Tuple
                if record.data_type == "hdt_endpoint":
                    # Endpoint records have additional fields
                    data_tuple = (
                        record.real_time,
                        record.sim_time,
                        record.scenario,
                        record.federate,
                        record.data_name,
                        record.receiving_federate,
                        record.receiving_endpoint,
                        self.helper.format_value_for_db(record.data_value),
                    )
                else:
                    # Regular records
                    data_tuple = (
                        record.real_time,
                        record.sim_time,
                        record.scenario,
                        record.federate,
                        record.data_name,
                        self.helper.format_value_for_db(record.data_value),
                    )

                grouped_records.setdefault(table_name, []).append(data_tuple)

            with self.helper.connection.cursor() as cursor:
                for table_name, data_tuples in grouped_records.items():
                    self._ensure_table_exists(table_name)

                    if table_name == "hdt_endpoint":
                        insert_query = sql.SQL("""
                            INSERT INTO {}.{} 
                            (real_time, sim_time, scenario, federate, data_name, 
                             receiving_federate, receiving_endpoint, data_value) 
                            VALUES %s""").format(
                            sql.Identifier(self.helper.analysis_name),
                            sql.Identifier(table_name),
                        )
                    else:
                        insert_query = sql.SQL("""
                            INSERT INTO {}.{} 
                            (real_time, sim_time, scenario, federate, data_name, data_value) 
                            VALUES %s""").format(
                            sql.Identifier(self.helper.analysis_name),
                            sql.Identifier(table_name),
                        )

                    execute_values(
                        cursor, insert_query, data_tuples, page_size=self.batch_size
                    )
            self.helper.connection.commit()
            return True
        except psycopg2.Error as e:
            logger.error(f"Failed to write records to PostgreSQL: {e}")
            self.helper.connection.rollback()
            return False

    # def write_endpoint_records(self, records: List[TSEndpointRecord]) -> bool:
    #     """Write endpoint records to PostgreSQL."""
    #     if not self._is_connected or not records:
    #         return True

    #     try:
    #         self.helper._ensure_endpoint_table_exists()

    #         data_tuples = [
    #             (
    #                 r.real_time,
    #                 r.sim_time,
    #                 r.scenario,
    #                 r.federate,
    #                 r.data_name,
    #                 r.receiving_federate,
    #                 r.receiving_endpoint,
    #                 self.helper.format_value_for_db(r.data_value),
    #             )
    #             for r in records
    #         ]

    #         with self.helper.connection.cursor() as cursor:
    #             insert_query = sql.SQL("""
    #                 INSERT INTO {}.endpoints
    #                 (real_time, sim_time, scenario, federate, data_name,
    #                 receiving_federate, receiving_endpoint, data_value)
    #                 VALUES %s""").format(sql.Identifier(self.helper.analysis_name))

    #             execute_values(
    #                 cursor, insert_query, data_tuples, page_size=self.batch_size
    #             )

    #         self.helper.connection.commit()
    #         return True
    #     except Exception as e:
    #         logger.error(f"Failed to write endpoint records: {e}")
    #         return False


class PostgreSQLTimeSeriesReader(TSDataReader):
    """PostgreSQL-based time-series data reader."""

    def __init__(
        self,
        *,  # Everything must be keyword
        location: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        analysis_name: Optional[str] = None,
        helper: Optional[_PostgresConnectionHelper] = None,
    ):
        super().__init__()
        self.helper: _PostgresConnectionHelper
        if helper:
            self.helper = helper
            self._owns_connection = False
        elif (
            location is not None
            and port is not None
            and database is not None
            and user is not None
            and password is not None
            and analysis_name is not None
        ):
            self.helper = _PostgresConnectionHelper(
                location, port, database, user, password, analysis_name
            )
            self._owns_connection = True
        else:
            raise ValueError(
                "Must provide either a 'helper' or all connection parameters (host, port, etc.)."
            )

    def connect(self) -> bool:
        """Establishes connection to the PostgreSQL server.

        Returns:
            bool: Flag indicating successful connection to the PostgreSQL
                database
        """
        if self._owns_connection:
            if not self.helper.connect():
                return False
        if self.helper.connection and not self.helper.connection.closed:
            self._is_connected = True
            return True
        logger.error(
            "PostgreSQL reader cannot connect; the connection helper is disconnected."
        )
        return False

    def disconnect(self) -> None:
        """Closes the connection to the PostgreSQL server.

        Returns:
            None
        """
        if self._owns_connection:
            self.helper.disconnect()
        self._is_connected = False

    def _get_tables_to_query(self, data_types: Optional[List[str]]) -> List[str]:
        """Gets list of tables in the PostgreSQL database

        Args:
            data_types (Optional[List[str]]): CST data types to be read
        Returns:
            List[str]: tables in PostgreSQL DB
        """
        assert self.helper.connection is not None, "Database not connected"
        with self.helper.connection.cursor() as cursor:
            query_str = "SELECT table_name FROM information_schema.tables WHERE table_schema = %s"
            params = [self.helper.analysis_name]

            if data_types:
                placeholders = ",".join(["%s"] * len(data_types))
                query_str += f" AND table_name IN ({placeholders})"
                params.extend(data_types)

            cursor.execute(query_str, params)
            return [row[0] for row in cursor.fetchall()]

    def read_data(
        self,
        start_time: Optional[float] = None,
        duration: Optional[float] = None,
        scenario_name: Optional[str | list] = None,
        federate_name: Optional[str | list] = None,
        data_name: Optional[str | list] = None,
        data_type: Optional[str | list] = None,
    ) -> pd.DataFrame:
        """Generic PostgreSQL data read

        Args:
            start_time (Optional[float], optional): Start time (ordinal time
                in seconds) for requested data. Defaults to None.
            duration (Optional[float], optional): Length of time (in seconds)
                from the data to read . Defaults to None.
            scenario_name (Optional[str | list], optional): Name(s) of scenario to read.
                Defaults to None.
            federate_name (Optional[str | list], optional): Name(s) of federate to
                read. Defaults to None.
            data_name (Optional[str | list], optional): Name(s) of data to read.
                Defaults to None.
            data_type (Optional[str | list], optional): Data type(s) to read. Defaults
                to None.

        Returns:
            pd.DataFrame: requested data
        """
        if not self._is_connected:
            logger.error("PostgreSQL reader not connected.")
            return pd.DataFrame()

        scenario_names = scenario_name
        federate_names = federate_name
        data_names = data_name
        data_types = data_type
        if isinstance(scenario_name, str):
            scenario_names = [scenario_name]
        if isinstance(federate_name, str):
            federate_names = [federate_name]
        if isinstance(data_name, str):
            data_names = [data_name]
        if isinstance(data_type, str):
            data_types = [data_type]

        assert self.helper.connection is not None, "Database not connected"
        all_data = []

        try:
            tables_to_query = self._get_tables_to_query(data_types)

            for table_name in tables_to_query:
                conditions = []
                params = []

                # Build WHERE conditions
                if scenario_names:
                    placeholders = ",".join(["%s"] * len(scenario_names))
                    conditions.append(sql.SQL(f"scenario IN ({placeholders})"))
                    params.extend(scenario_names)

                if federate_names:
                    placeholders = ",".join(["%s"] * len(federate_names))
                    conditions.append(sql.SQL(f"federate IN ({placeholders})"))
                    params.extend(federate_names)

                if data_names:
                    placeholders = ",".join(["%s"] * len(data_names))
                    conditions.append(sql.SQL(f"data_name IN ({placeholders})"))
                    params.extend(data_names)

                if start_time is not None:
                    conditions.append(sql.SQL("sim_time >= %s"))
                    params.append(start_time)

                if duration is not None:
                    end_time = (start_time or 0.0) + duration
                    conditions.append(sql.SQL("sim_time < %s"))
                    params.append(end_time)

                where_clause = (
                    sql.SQL(" AND ").join(conditions) if conditions else sql.SQL("TRUE")
                )

                query = sql.SQL(
                    "SELECT * FROM {}.{} WHERE {} ORDER BY sim_time"
                ).format(
                    sql.Identifier(self.helper.analysis_name),
                    sql.Identifier(table_name),
                    where_clause,
                )

                with self.helper.connection.cursor(
                    cursor_factory=RealDictCursor
                ) as cursor:
                    cursor.execute(query, params)
                    results = cursor.fetchall()
                    if results:
                        df = pd.DataFrame(results)
                        df["data_value"] = df["data_value"].apply(
                            lambda v: self.helper.parse_value_from_db(v, table_name)
                        )
                        df["real_time"] = pd.to_datetime(df["real_time"])
                        all_data.append(df)

            if not all_data:
                return pd.DataFrame()

            return (
                pd.concat(all_data, ignore_index=True)
                .sort_values("sim_time")
                .reset_index(drop=True)
            )
        except psycopg2.Error as e:
            logger.error(f"Failed to read data from PostgreSQL: {e}")
            return pd.DataFrame()

    def _query_distinct_column(self, column_name: str) -> List[str]:
        """Produces a list of distinct values stored in the metadata store

        Args:
            column_name (str): _description_

        Returns:
            List[str]: _description_
        """
        if not self._is_connected:
            return []
        assert self.helper.connection is not None, "Database not connected"
        all_values: set = set()
        tables = self._get_tables_to_query(None)
        with self.helper.connection.cursor() as cursor:
            for table in tables:
                query = sql.SQL("SELECT DISTINCT {} FROM {}.{}").format(
                    sql.Identifier(column_name),
                    sql.Identifier(self.helper.analysis_name),
                    sql.Identifier(table),
                )
                cursor.execute(query)
                all_values.update(row[0] for row in cursor.fetchall())
        return sorted(list(all_values))

    def list_scenarios(self) -> List[str]:
        """Produces a list of scenarios stored in the metadata store

        Returns:
            List[str]: list of scenarios
        """
        return self._query_distinct_column("scenario")

    def list_federates(self) -> List[str]:
        """Produces a list of federations stored in the metadata store

        Returns:
            List[str]: list of federations
        """
        return self._query_distinct_column("federate")

    def list_data_types(self) -> List[str]:
        """Produces the list of data types in PostgreSQL database

        Returns:
            List[str]: Data types in database
        """
        if not self._is_connected:
            return []
        return self._get_tables_to_query(None)


class PostgreSQLTimeSeriesManager(TSDataManager):
    """Joint PostgreSQL time-series manager using composition."""

    def __init__(
        self,
        *,  # Everything must be keyword
        location: str,
        port: int,
        database: str,
        user: str,
        password: str,
        analysis_name: str,
        use_timescale: bool = False,
        **kwargs,
    ):
        super().__init__()
        self.helper: _PostgresConnectionHelper = _PostgresConnectionHelper(
            location, port, database, user, password, analysis_name, use_timescale
        )
        self.writer: PostgreSQLTimeSeriesWriter = PostgreSQLTimeSeriesWriter(
            helper=self.helper, **kwargs
        )
        self.reader: PostgreSQLTimeSeriesReader = PostgreSQLTimeSeriesReader(
            helper=self.helper
        )

    def connect(self) -> bool:
        """Establishes connection to the PostgreSQL server.

        Returns:
            bool: Flag indicating successful connection to the PostgreSQL
                database
        """
        if not self.helper.connect():
            return False
        self.writer.connect()
        self.reader.connect()
        self._is_connected = True
        return self._is_connected

    def disconnect(self) -> None:
        """Closes the connection to the PostgreSQL server.

        Returns:
            None
        """
        self.helper.disconnect()
        self.writer.disconnect()
        self.reader.disconnect()
        self._is_connected = False

    def list_scenarios(self) -> List[str]:
        """Produces a list of scenarios stored in the metadata store

        Returns:
            List[str]: list of scenarios
        """
        return self.reader.list_scenarios()

    def list_federates(self) -> List[str]:
        """Produces a list of federations stored in the metadata store

        Returns:
            List[str]: list of federations
        """
        return self.reader.list_federates()

    def list_data_types(self) -> List[str]:
        """Produces a list of data types in the PostgreSQL database

        Returns:
            List[str]: ist of data types in the PostgreSQL database
        """
        return self.reader.list_data_types()

    def get_time_range(self, **kwargs) -> Dict[str, float]:
        """Produces time range of data in PostgreSQL database

        Returns:
            Dict[str, float]: Time range information as::

                {
                    "min_time": float
                    "max_time": float
                }

            Time values are in ordinal time
        """
        if not self._is_connected:
            return {"min_time": 0.0, "max_time": 0.0}
        df = self.reader.read_data(**kwargs)
        if df.empty:
            return {"min_time": 0.0, "max_time": 0.0}
        return {
            "min_time": float(df["sim_time"].min()),
            "max_time": float(df["sim_time"].max()),
        }

    def _delete_by_column(self, column_name: str, value: str) -> bool:
        """ Deletes records (rows) where specified column matches specified 
        value

        Args:
            column_name (str): Name of column used to check for target value
            value (str): Target value being evaluated

        Returns:
            bool: Flag indicating whether data was deleted
        """
        if not self._is_connected:
            logger.error("PostgreSQL manager not connected.")
            return False
        assert self.helper.connection is not None, "Database not connected"
        try:
            tables = self.reader.list_data_types()
            with self.helper.connection.cursor() as cursor:
                for table in tables:
                    query = sql.SQL("DELETE FROM {}.{} WHERE {} = %s").format(
                        sql.Identifier(self.helper.analysis_name),
                        sql.Identifier(table),
                        sql.Identifier(column_name),
                    )
                    cursor.execute(query, (value,))
            self.helper.connection.commit()
            logger.debug(f"Deleted data where {column_name} = '{value}'")
            return True
        except psycopg2.Error as e:
            logger.error(f"Failed to delete data where {column_name} = '{value}': {e}")
            self.helper.connection.rollback()
            return False

    def delete_scenario_data(self, scenario_name: str) -> bool:
        """Delete data from PostgreSQL database from specified scenario

        Args:
            scenario_name (str): name of scenario to delete from database

        Returns:
            bool: Flag indicating data was deleted
        """
        return self._delete_by_column("scenario", scenario_name)

    def delete_federate_data(self, federate_name: str) -> bool:
        """Delete data from PostgreSQL database for specified data

        Args:
            federate_name:

        Returns:
            bool: Flag indicating data was deleted
        """
        return self._delete_by_column("federate", federate_name)
