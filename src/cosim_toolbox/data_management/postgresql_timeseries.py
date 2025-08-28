"""
PostgreSQL-based time-series data management for CoSim Toolbox.
Refactored to use a composition-based architecture for clarity,
testability, and maintainability.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

try:
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extras import RealDictCursor, execute_values

    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

from data_management.abstractions import (
    TSDataReader,
    TSDataManager,
    TSDataWriter,
    TSRecord,
)
from data_management.validation import ValidationError, validate_database_identifier

logger = logging.getLogger(__name__)


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
        """Establishes and validates the PostgreSQL connection."""
        if self.connection and not self.connection.closed:
            return True
        try:
            validate_database_identifier(self.analysis_name, "schema")
            self.connection = psycopg2.connect(
                host=self.conn_params["host"],
                port=self.conn_params["port"],
                database=self.conn_params["database"],
                user=self.conn_params["user"],
                password=self.conn_params["password"],
            )
            self.connection.autocommit = False
            self._ensure_schema_exists()
            logger.info(
                f"PostgreSQL helper connected to: {self.conn_params['host']}/{self.conn_params['database']}"
            )
            return True
        except (ValidationError, psycopg2.Error) as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            self.connection = None
            return False

    def disconnect(self) -> None:
        """Closes the PostgreSQL connection."""
        if self.connection and not self.connection.closed:
            self.connection.close()
            logger.debug("PostgreSQL helper disconnected.")
        self.connection = None

    def _ensure_schema_exists(self) -> None:
        assert self.connection is not None, "Database not connected"
        with self.connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
                    sql.Identifier(self.analysis_name)
                )
            )
        self.connection.commit()

    def get_data_type_info(self, record: TSRecord) -> Tuple[str, str]:
        """
        Get table name and PostgreSQL column type from TSRecord.

        Args:
            record (TSRecord): The record containing data_type and data_value

        Returns:
            Tuple[str, str]: (table_suffix, postgres_column_type)
        """
        # If data_type is explicitly set, use it
        if record.data_type:
            table_suffix = record.data_type.lower()
        else:
            # Fallback to auto-detection (for backward compatibility)
            table_suffix = self._auto_detect_type(record.data_value)

        # Map HDT type to PostgreSQL column type
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

        postgres_type = type_mapping.get(table_suffix, "TEXT")
        return (table_suffix, postgres_type)

    def get_data_type_info(self, value: Any) -> Tuple[str, str]:
        if isinstance(value, bool):
            return ("hdt_boolean", "BOOLEAN")
        if isinstance(value, int):
            return ("hdt_integer", "BIGINT")
        if isinstance(value, float):
            return ("hdt_double", "DOUBLE PRECISION")
        if isinstance(value, complex):
            return ("hdt_complex", "TEXT")
        if isinstance(value, (list, tuple)):
            return ("hdt_vector", "TEXT")
        return ("hdt_string", "TEXT")

    def format_value_for_db(self, value: Any) -> Any:
        if isinstance(value, (list, tuple)):
            return json.dumps(value)
        if isinstance(value, complex):
            return str(value)
        return value

    def parse_value_from_db(self, value: Any, table_suffix: str) -> Any:
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
        if self._owns_connection:
            self.helper.disconnect()
        self._is_connected = False
        self._table_cache.clear()

    def _ensure_table_exists(self, table_suffix: str, postgres_type: str) -> None:
        table_key = f"{self.helper.analysis_name}.{table_suffix}"
        if table_key in self._table_cache:
            return
        assert self.helper.connection is not None, "Database not connected"
        with self.helper.connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("""
                CREATE TABLE IF NOT EXISTS {schema}.{table} (
                    id SERIAL PRIMARY KEY, real_time TIMESTAMPTZ NOT NULL, sim_time DOUBLE PRECISION NOT NULL,
                    scenario TEXT NOT NULL, federate TEXT NOT NULL, data_name TEXT NOT NULL,
                    data_value {pg_type} NOT NULL, created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                )""").format(
                    schema=sql.Identifier(self.helper.analysis_name),
                    table=sql.Identifier(table_suffix),
                    pg_type=sql.SQL(postgres_type),
                )
            )
            if self.helper.use_timescale:
                try:
                    full_table_name = f"{self.helper.analysis_name}.{table_suffix}"
                    cursor.execute(
                        "SELECT 1 FROM timescaledb_information.hypertables WHERE hypertable_schema = %s AND hypertable_name = %s",
                        (self.helper.analysis_name, table_suffix),
                    )
                    if cursor.fetchone() is None:
                        logger.info(f"Creating hypertable for {full_table_name}")
                        cursor.execute(
                            sql.SQL("SELECT create_hypertable(%s, 'real_time')"),
                            (full_table_name,),
                        )
                except psycopg2.Error as ts_error:
                    logger.warning(
                        f"Could not create hypertable for {table_key}. Is TimescaleDB enabled? Error: {ts_error}"
                    )
                    self.helper.connection.rollback()
            for col in ["sim_time", "scenario", "federate", "data_name"]:
                idx_name = sql.Identifier(f"idx_{table_suffix}_{col}")
                cursor.execute(
                    sql.SQL(
                        "CREATE INDEX IF NOT EXISTS {idx} ON {schema}.{table} ({col})"
                    ).format(
                        idx=idx_name,
                        schema=sql.Identifier(self.helper.analysis_name),
                        table=sql.Identifier(table_suffix),
                        col=sql.Identifier(col),
                    )
                )
        self.helper.connection.commit()
        self._table_cache.add(table_key)

    def write_records(self, records: List[TSRecord]) -> bool:
        if not self._is_connected:
            logger.error("PostgreSQL writer not connected.")
            return False
        assert self.helper.connection is not None, "Database not connected"
        if not records:
            return True
        try:
            grouped_records: Dict[Tuple[str, str], List[tuple]] = {}
            for record in records:
                table_suffix, pg_type = self.helper.get_data_type_info(
                    record.data_value
                )
                key = (table_suffix, pg_type)
                data_tuple = (
                    record.real_time,
                    record.sim_time,
                    record.scenario,
                    record.federate,
                    record.data_name,
                    self.helper.format_value_for_db(record.data_value),
                )
                grouped_records.setdefault(key, []).append(data_tuple)
            with self.helper.connection.cursor() as cursor:
                for (table_suffix, pg_type), data_tuples in grouped_records.items():
                    self._ensure_table_exists(table_suffix, pg_type)
                    insert_query = sql.SQL(
                        "INSERT INTO {}.{} (real_time, sim_time, scenario, federate, data_name, data_value) VALUES %s"
                    ).format(
                        sql.Identifier(self.helper.analysis_name),
                        sql.Identifier(table_suffix),
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
        if self._owns_connection:
            self.helper.disconnect()
        self._is_connected = False

    def _get_tables_to_query(self, data_type: Optional[str]) -> List[str]:
        assert self.helper.connection is not None, "Database not connected"
        with self.helper.connection.cursor() as cursor:
            query_str = "SELECT table_name FROM information_schema.tables WHERE table_schema = %s"
            params = [self.helper.analysis_name]
            if data_type:
                query_str += " AND table_name = %s"
                params.append(data_type)
            cursor.execute(query_str, params)
            return [row[0] for row in cursor.fetchall()]

    def read_data(
        self,
        start_time: Optional[float] = None,
        duration: Optional[float] = None,
        scenario_name: Optional[str] = None,
        federate_name: Optional[str] = None,
        data_name: Optional[str] = None,
        data_type: Optional[str] = None,
    ) -> pd.DataFrame:
        if not self._is_connected:
            logger.error("PostgreSQL reader not connected.")
            return pd.DataFrame()
        assert self.helper.connection is not None, "Database not connected"
        all_data = []
        try:
            tables_to_query = self._get_tables_to_query(data_type)
            for table_suffix in tables_to_query:
                conditions = []
                params = []
                if scenario_name:
                    conditions.append(sql.SQL("scenario = %s"))
                    params.append(scenario_name)
                if federate_name:
                    conditions.append(sql.SQL("federate = %s"))
                    params.append(federate_name)
                if data_name:
                    conditions.append(sql.SQL("data_name = %s"))
                    params.append(data_name)
                if start_time is not None:
                    conditions.append(sql.SQL("sim_time >= %s"))
                    params.append(str(start_time))
                if duration is not None:
                    end_time = (start_time or 0.0) + duration
                    conditions.append(sql.SQL("sim_time < %s"))
                    params.append(str(end_time))

                where_clause = (
                    sql.SQL(" AND ").join(conditions) if conditions else sql.SQL("TRUE")
                )
                query = sql.SQL(
                    "SELECT * FROM {}.{} WHERE {} ORDER BY sim_time"
                ).format(
                    sql.Identifier(self.helper.analysis_name),
                    sql.Identifier(table_suffix),
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
                            lambda v: self.helper.parse_value_from_db(v, table_suffix)
                        )
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
        return self._query_distinct_column("scenario")

    def list_federates(self) -> List[str]:
        return self._query_distinct_column("federate")

    def list_data_types(self) -> List[str]:
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
        if not self.helper.connect():
            return False
        self.writer.connect()
        self.reader.connect()
        self._is_connected = True
        return self._is_connected

    def disconnect(self) -> None:
        self.helper.disconnect()
        self.writer.disconnect()
        self.reader.disconnect()
        self._is_connected = False

    def list_scenarios(self) -> List[str]:
        return self.reader.list_scenarios()

    def list_federates(self) -> List[str]:
        return self.reader.list_federates()

    def list_data_types(self) -> List[str]:
        return self.reader.list_data_types()

    def get_time_range(self, **kwargs) -> Dict[str, float]:
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
        return self._delete_by_column("scenario", scenario_name)

    def delete_federate_data(self, federate_name: str) -> bool:
        return self._delete_by_column("federate", federate_name)
