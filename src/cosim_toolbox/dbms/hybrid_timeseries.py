"""
Hybrid CSV-to-PostgreSQL time-series data management for CoSim Toolbox.
Writes data to CSV files during operation and uploads to PostgreSQL at the end.
Uses a composition-based architecture for clarity, testability, and maintainability.

@author Nathan Gray
"""

import logging
from typing import Dict, List, Optional

import pandas as pd

from .abstractions import TSDataManager, TSDataReader, TSDataWriter, TSRecord
from .csv_timeseries import CSVTimeSeriesReader, CSVTimeSeriesWriter, _CSVHelper
from .postgresql_timeseries import (
    PostgreSQLTimeSeriesReader,
    PostgreSQLTimeSeriesWriter,
    _PostgresConnectionHelper,
)

logger = logging.getLogger(__name__)


class HybridCSVtoPostgresWriter(TSDataWriter):
    """Hybrid writer that writes to CSV during operation and uploads to PostgreSQL on disconnect."""

    def __init__(
        self,
        *,
        csv_location: Optional[str] = None,
        analysis_name: str = "default",
        location: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        use_timescale: bool = False,
        batch_size: int = 1000,
        csv_helper: Optional[_CSVHelper] = None,
        pg_helper: Optional[_PostgresConnectionHelper] = None,
    ):
        """Initialize the hybrid writer with CSV and PostgreSQL configurations."""
        super().__init__()
        # CSV setup for temporary storage
        self.csv_writer: CSVTimeSeriesWriter
        if csv_helper:
            self.csv_writer = CSVTimeSeriesWriter(helper=csv_helper)
        else:
            self.csv_writer = CSVTimeSeriesWriter(
                location=csv_location, analysis_name=analysis_name
            )

        # PostgreSQL setup for final upload
        self.pg_writer: PostgreSQLTimeSeriesWriter
        if pg_helper:
            self.pg_writer = PostgreSQLTimeSeriesWriter(
                helper=pg_helper, batch_size=batch_size
            )
        elif all([location, port, database, user, password]):
            self.pg_writer = PostgreSQLTimeSeriesWriter(
                location=location,
                port=port,
                database=database,
                user=user,
                password=password,
                analysis_name=analysis_name,
                use_timescale=use_timescale,
                batch_size=batch_size,
            )
        else:
            raise ValueError(
                "Must provide either 'pg_helper' or all PostgreSQL connection parameters."
            )

    def connect(self) -> bool:
        """Connect to CSV writer initially (PostgreSQL connection deferred until upload)."""
        success = self.csv_writer.connect()
        if success:
            self._is_connected = True
            logger.info("Hybrid writer connected to CSV storage.")
        else:
            logger.error("Failed to connect hybrid writer to CSV storage.")
        return success

    def disconnect(self) -> None:
        """Disconnect from CSV and upload data to PostgreSQL."""
        if not self._is_connected:
            logger.warning("Hybrid writer not connected, skipping disconnect.")
            return

        # Flush any remaining buffered data to CSV
        self.flush()

        # Upload CSV data to PostgreSQL
        success = self._upload_to_postgres()
        if success:
            logger.info("Successfully uploaded CSV data to PostgreSQL.")
        else:
            logger.error("Failed to upload CSV data to PostgreSQL.")

        # Disconnect from both backends
        self.csv_writer.disconnect()
        self.pg_writer.disconnect()
        self._is_connected = False
        logger.debug("Hybrid writer disconnected.")

    def _upload_to_postgres(self) -> bool:
        """Read data from CSV files and upload to PostgreSQL."""
        if not self.csv_writer.is_connected:
            logger.error("CSV writer not connected for upload.")
            return False

        # Connect to PostgreSQL
        if not self.pg_writer.connect():
            logger.error("Failed to connect to PostgreSQL for upload.")
            return False

        try:
            # Get list of federates and data types from CSV storage
            federate_dirs = self.csv_writer.helper.analysis_path.iterdir()
            records_to_upload: List[TSRecord] = []

            for federate_path in federate_dirs:
                if not federate_path.is_dir():
                    continue
                federate_name = federate_path.name
                for csv_file in federate_path.glob("*.csv"):
                    if not csv_file.exists() or csv_file.stat().st_size == 0:
                        continue
                    data_type = csv_file.stem
                    df = pd.read_csv(csv_file)
                    for _, row in df.iterrows():
                        record = TSRecord(
                            real_time=pd.to_datetime(row["real_time"]).to_pydatetime(),
                            sim_time=float(row["sim_time"]),
                            scenario=str(row["scenario"]),
                            federate=str(row["federate"]),
                            data_name=str(row["data_name"]),
                            data_value=self.csv_writer.helper.parse_value_from_csv(
                                str(row["data_value"]), data_type
                            ),
                            receiving_federate=row.get("receiving_federate"),
                            receiving_endpoint=row.get("receiving_endpoint"),
                            data_type=data_type,
                        )
                        records_to_upload.append(record)

            # Batch upload to PostgreSQL
            if records_to_upload:
                success = self.pg_writer.write_records(records_to_upload)
                if not success:
                    logger.error("Failed to write records to PostgreSQL during upload.")
                    return False
            return True
        except Exception as e:
            logger.error(f"Error during CSV to PostgreSQL upload: {e}")
            return False
        finally:
            self.pg_writer.disconnect()

    def write_records(self, records: List[TSRecord]) -> bool:
        """Write records to CSV storage."""
        return self.csv_writer.write_records(records)

    def add_record(self, record: TSRecord) -> None:
        """Add a single record to the CSV buffer."""
        self.csv_writer.add_record(record)

    def flush(self) -> bool:
        """Flush buffered records to CSV storage."""
        return self.csv_writer.flush()


class HybridCSVtoPostgresManager(TSDataManager):
    """Manager for hybrid CSV-to-PostgreSQL time-series data handling."""

    def __init__(
        self,
        *,
        csv_location: str,
        analysis_name: str = "default",
        location: str,
        port: int,
        database: str,
        user: str,
        password: str,
        use_timescale: bool = False,
        batch_size: int = 1000,
        **kwargs,
    ):
        """Initialize the hybrid manager with CSV and PostgreSQL configurations."""
        super().__init__(**kwargs)
        # Shared helpers for CSV and PostgreSQL components
        self.csv_helper = _CSVHelper(csv_location, analysis_name)
        self.pg_helper = _PostgresConnectionHelper(
            location,
            port,
            database,
            user,
            password,
            analysis_name,
            use_timescale,
        )
        # Writer for CSV with deferred PostgreSQL upload
        self.writer = HybridCSVtoPostgresWriter(
            csv_helper=self.csv_helper, pg_helper=self.pg_helper, batch_size=batch_size
        )
        # Reader initially uses CSV, can switch to PostgreSQL after upload if needed
        self.reader = CSVTimeSeriesReader(helper=self.csv_helper)
        self.pg_reader = PostgreSQLTimeSeriesReader(helper=self.pg_helper)
        self._use_pg_reader = False  # Flag to switch reader after upload

    def connect(self) -> bool:
        """Connect to CSV storage for writing and reading initially."""
        writer_connected = self.writer.connect()
        reader_connected = self.reader.connect()
        self._is_connected = writer_connected and reader_connected
        if self._is_connected:
            logger.info("Hybrid manager connected to CSV storage.")
        return self._is_connected

    def disconnect(self) -> None:
        """Disconnect from CSV and upload to PostgreSQL, switch reader if successful."""
        if not self._is_connected:
            logger.warning("Hybrid manager not connected, skipping disconnect.")
            return

        # Disconnect writer (triggers upload to PostgreSQL)
        self.writer.disconnect()

        # Check if PostgreSQL upload was successful by attempting connection
        if self.pg_reader.connect():
            self._use_pg_reader = True
            self.reader.disconnect()
            logger.info("Hybrid manager switched to PostgreSQL reader after upload.")
        else:
            logger.warning("PostgreSQL upload failed, continuing with CSV reader.")
            self.pg_reader.disconnect()

        self._is_connected = False
        logger.debug("Hybrid manager disconnected.")

    def read_data(self, **kwargs) -> pd.DataFrame:
        """Read data from either CSV or PostgreSQL based on upload status."""
        if self._use_pg_reader:
            return self.pg_reader.read_data(**kwargs)
        return self.reader.read_data(**kwargs)

    def list_federates(self) -> List[str]:
        """List federates from the active reader."""
        if self._use_pg_reader:
            return self.pg_reader.list_federates()
        return self.reader.list_federates()

    def list_data_types(self, federate_names: Optional[List[str]] = None) -> List[str]:
        """List data types from the active reader."""
        if self._use_pg_reader:
            return self.pg_reader.list_data_types()
        return self.reader.list_data_types(federate_names)

    def list_scenarios(self) -> List[str]:
        """List scenarios from the active reader."""
        if self._use_pg_reader:
            return self.pg_reader.list_scenarios()
        return self.reader.list_scenarios()

    def get_time_range(self, **kwargs) -> Dict[str, float]:
        """Get time range from the active reader."""
        if self._use_pg_reader:
            return self.pg_reader.get_time_range(**kwargs)
        return self.reader.get_time_range(**kwargs)

    def delete_scenario_data(self, scenario_name: str) -> bool:
        """Delete scenario data if using PostgreSQL reader, otherwise not supported."""
        if self._use_pg_reader:
            # Delegate to PostgreSQL manager logic if needed
            logger.warning(
                "Scenario deletion requires manual handling after upload to PostgreSQL."
            )
            return False
        logger.warning("Scenario deletion not supported in CSV mode.")
        return False

    def delete_federate_data(self, federate_name: str) -> bool:
        """Delete federate data if using PostgreSQL reader, otherwise delete from CSV."""
        if self._use_pg_reader:
            # Delegate to PostgreSQL manager logic if needed
            logger.warning(
                "Federate deletion requires manual handling after upload to PostgreSQL."
            )
            return False
        federate_path = self.csv_helper.analysis_path / federate_name
        if federate_path.exists() and federate_path.is_dir():
            import shutil

            shutil.rmtree(federate_path)
            logger.debug(f"Deleted CSV data for federate: {federate_name}")
            return True
        logger.warning(f"Federate directory not found in CSV: {federate_name}")
        return False

    @property
    def location(self) -> str:
        """Return CSV location before upload, PostgreSQL location after."""
        if self._use_pg_reader:
            return self.pg_helper.conn_params["host"]
        return str(self.csv_helper.location)

    @property
    def analysis_name(self) -> str:
        """Return the analysis name."""
        return self.csv_helper.analysis_name
