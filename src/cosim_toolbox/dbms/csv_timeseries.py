"""
CSV file-based time-series data management for CoSim Toolbox.
Refactored to use a composition-based architecture for clarity,
testability, and maintainability.

@author Nathan Gray
"""

import csv
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from .abstractions import TSDataWriter, TSDataReader, TSDataManager, TSRecord
from .validation import validate_name, ValidationError, safe_name_log

logger = logging.getLogger(__name__)


class _CSVHelper:
    """Manages paths and data formatting logic for CSV time-series storage."""

    CSV_HEADERS = [
        "real_time",
        "sim_time",
        "scenario",
        "federate",
        "data_name",
        "data_value",
    ]
    ENDPOINT_CSV_HEADERS = [
        "real_time",
        "sim_time",
        "scenario",
        "federate",
        "data_name",
        "receiving_federate",
        "receiving_endpoint",
        "data_value",
    ]

    def __init__(self, location: str, analysis_name: str):
        validate_name(analysis_name, context="analysis")
        self.location = Path(location)
        self.analysis_name = analysis_name
        self.analysis_path = self.location / self.analysis_name

    def get_file_path(self, federate_name: str, data_type: str) -> Path:
        """Get the file path for a specific federate and data type.
        For the CSV data backend each federate has its own folder to store
        data and each data type is stored in its own file.

        Args:
            federate_name (str): name of federate
            data_type (str): data type

        Returns:
            Path: Path to CSV file
        """
        federate_path = self.analysis_path / federate_name
        return federate_path / f"{data_type}.csv"

    @staticmethod
    def get_data_type(value: Any) -> str:
        """Determine the CST data type for a given value.

        Args:
            value (Any): value whose data type is being determined

        Returns:
            str: String defining the data type. Value will be one of the
                following:
                    "hdt_boolean"
                    "hdt_integer"
                    "hdt_double"
                    "hdt_complex"
                    "hdt_string"
                    "hdt_complex_vector"
                    "hdt_vector"
                    "hdt_string"
        """
        if isinstance(value, bool):
            return "hdt_boolean"
        if isinstance(value, int):
            return "hdt_integer"
        if isinstance(value, float):
            return "hdt_double"
        if isinstance(value, complex):
            return "hdt_complex"
        if isinstance(value, str):
            return "hdt_string"
        if isinstance(value, (list, tuple)):
            return (
                "hdt_complex_vector"
                if value and isinstance(value[0], complex)
                else "hdt_vector"
            )
        return "hdt_string"  # Default for unknown types

    @staticmethod
    def format_value_for_csv(value: Any) -> str:
        """Format a value for CSV storage.

        Args:
            value (Any): value to be formatted

        Returns:
            str: formatted value as string
        """
        if isinstance(value, (list, tuple)):
            return json.dumps(value)
        if isinstance(value, complex):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    @staticmethod
    def parse_value_from_csv(value_str: str, data_type: str) -> Any:
        """Parse a value from CSV string back to appropriate Python type.

        Args:
            value_str (str): Numerical value as string to be converted
            data_type (str): defines data type of string to be converted
                Must be one of the following values:
                    "hdt_boolean"
                    "hdt_integer"
                    "hdt_double"
                    "hdt_complex"
                    "hdt_complex_vector"
                    "hdt_vector"

        Returns:
            Any: Data from passed in string as the specified data type
        """
        try:
            if data_type == "hdt_double":
                return float(value_str)
            if data_type == "hdt_integer":
                return int(value_str)
            if data_type == "hdt_boolean":
                return value_str.lower() in ("true", "1", "yes")
            if data_type == "hdt_complex":
                return complex(value_str)
            if data_type in ("hdt_vector", "hdt_complex_vector"):
                return json.loads(value_str)
            return value_str
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning(
                f"Failed to parse value '{safe_name_log(value_str)}' as {data_type}: {e}"
            )
            return value_str


class CSVTimeSeriesWriter(TSDataWriter):
    """CSV file-based time-series data writer."""

    def __init__(
        self,
        *,
        location: Optional[str] = None,
        analysis_name: str = "default",
        helper: Optional[_CSVHelper] = None,
    ):
        """Initialize the CSV writer.

        For standalone use:
            writer = CSVTimeSeriesWriter(location="/path/to/data", analysis_name="my_analysis")
        For managed use (by CSVTimeSeriesManager):
            helper = _CSVHelper(...)
            writer = CSVTimeSeriesWriter(helper=helper)
        """
        super().__init__()
        self.helper: _CSVHelper
        if helper:
            self.helper = helper
        elif location:
            self.helper = _CSVHelper(location, analysis_name)
        else:
            raise ValueError("Either 'helper' or 'location' must be provided.")

    def _ensure_file_exists(self, file_path: Path) -> None:
        """Ensure the CSV file exists with proper headers.

        Args:
            file_path (Path): Path to CSV file whose existence is being
                evaluated.

        Returns:
            None
        """
        headers = self.helper.CSV_HEADERS
        if file_path.name == "hdt_endpoint.csv":
            headers = self.helper.ENDPOINT_CSV_HEADERS
        if not file_path.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)

    def connect(self) -> bool:
        """Create directory structure if it doesn't exist.

        Returns:
            bool: Flag indicating whether directory structure has been
                created.
        """
        try:
            self.helper.analysis_path.mkdir(parents=True, exist_ok=True)
            self._is_connected = True
            logger.info(
                f"CSV time-series writer connected to: {self.helper.analysis_path}"
            )
            return True
        except (OSError, IOError) as e:
            logger.error(f"Failed to create directories for CSV writer: {e}")
            return False

    def disconnect(self) -> None:
        """Close connection (no-op for files, but maintains consistency).

        Returns:
            None
        """
        self._is_connected = False
        logger.debug("CSV time-series writer disconnected")

    def write_records(self, records: List[TSRecord]) -> bool:
        """Write TSRecord objects to CSV files.

        Args:
            records (List[TSRecord]): Records (data) to be written to the data
                backend

        Returns:
            bool: flag indicating whether the data was written to the data
                backend
        """
        if not self.is_connected:
            logger.error("CSV writer not connected. Call connect() first.")
            return False
        if not records:
            return True
        try:
            grouped_records: Dict[tuple[str, str], List[TSRecord]] = {}
            for record in records:
                validate_name(record.federate, context="federate")
                key = (record.federate, record.data_type)
                grouped_records.setdefault(key, []).append(record)

            for (federate_name, data_type), group_records in grouped_records.items():
                file_path = self.helper.get_file_path(federate_name, data_type)
                self._ensure_file_exists(file_path)
                with open(file_path, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    for record in group_records:
                        row = [
                            record.real_time.isoformat(),
                            record.sim_time,
                            record.scenario,
                            record.federate,
                            record.data_name,
                        ]
                        if data_type == "hdt_endpoint":
                            row.extend(
                                [
                                    record.receiving_federate,
                                    record.receiving_endpoint,
                                ]
                            )
                        row.append(self.helper.format_value_for_csv(record.data_value))
                        writer.writerow(row)
            logger.debug(f"Wrote {len(records)} records to CSV files")
            return True
        except ValidationError as e:
            logger.error(f"Validation error writing CSV records: {e}")
            return False
        except (OSError, IOError) as e:
            logger.error(f"File I/O error writing CSV records: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error writing CSV records: {e}")
            return False


class CSVTimeSeriesReader(TSDataReader):
    """CSV file-based time-series data reader."""

    def __init__(
        self,
        *,
        location: Optional[str] = None,
        analysis_name: str = "default",
        helper: Optional[_CSVHelper] = None,
    ):
        """
        Initialize the CSV reader.

        For standalone use:
            reader = CSVTimeSeriesReader(location="/path/to/data", analysis_name="my_analysis")
        For managed use (by CSVTimeSeriesManager):
            helper = _CSVHelper(...)
            reader = CSVTimeSeriesReader(helper=helper)
        """
        super().__init__()
        self.helper: _CSVHelper
        if helper:
            self.helper = helper
        elif location:
            self.helper = _CSVHelper(location, analysis_name)
        else:
            raise ValueError("Either 'helper' or 'location' must be provided.")

    def connect(self) -> bool:
        """Verify that the directory structure exists.

        Returns:
            bool: flag indicated whether the connection to the data backend
                exists
        """
        if not self.helper.analysis_path.exists():
            logger.warning(f"Analysis path does not exist: {self.helper.analysis_path}")
        self._is_connected = True
        logger.info(f"CSV time-series reader connected to: {self.helper.analysis_path}")
        return True

    def disconnect(self) -> None:
        """Close connection (no-op for files).

        Returns:
            None
        """
        self._is_connected = False
        logger.debug("CSV time-series reader disconnected")

    def read_data(
        self,
        start_time: Optional[float] = None,
        duration: Optional[float] = None,
        scenario_name: Optional[str | list] = None,
        federate_name: Optional[str | list] = None,
        data_name: Optional[str | list] = None,
        data_type: Optional[str | list] = None,
    ) -> pd.DataFrame:
        """Read time-series data from CSV files.

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
        if not self.is_connected:
            logger.error("CSV reader not connected. Call connect() first.")
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

        if not self.helper.analysis_path.exists():
            return pd.DataFrame()

        federate_dirs = (
            (self.helper.analysis_path / _fed_name for _fed_name in federate_names)
            if federate_name
            else self.helper.analysis_path.iterdir()
        )

        all_dataframes = []

        for federate_path in federate_dirs:
            if not federate_path.is_dir():
                continue

            csv_files = (
                (federate_path / f"{_data_type}.csv" for _data_type in data_types)
                if data_type
                else federate_path.glob("*.csv")
            )

            for csv_file in csv_files:
                if not csv_file.exists() or csv_file.stat().st_size == 0:
                    continue
                try:
                    df = pd.read_csv(csv_file)
                    current_data_type = csv_file.stem
                    df["data_value"] = df["data_value"].apply(
                        lambda x: self.helper.parse_value_from_csv(
                            str(x), current_data_type
                        )
                    )
                    df["real_time"] = pd.to_datetime(df["real_time"])
                    all_dataframes.append(df)
                except Exception as e:
                    logger.warning(f"Failed to read or parse CSV file {csv_file}: {e}")

        if not all_dataframes:
            return pd.DataFrame()

        combined_df = pd.concat(all_dataframes, ignore_index=True)

        # Apply filters
        query_parts = []

        if scenario_names:
            scenario_conditions = [f"scenario == '{name}'" for name in scenario_names]
            query_parts.append(f"({' or '.join(scenario_conditions)})")

        if federate_names:
            federate_conditions = [f"federate == '{name}'" for name in federate_names]
            query_parts.append(f"({' or '.join(federate_conditions)})")

        if data_names:
            data_name_conditions = [f"data_name == '{name}'" for name in data_names]
            query_parts.append(f"({' or '.join(data_name_conditions)})")

        if start_time is not None:
            query_parts.append(f"sim_time >= {start_time}")

        if duration is not None:
            end_time = (start_time or 0) + duration
            query_parts.append(f"sim_time < {end_time}")

        filtered_df = (
            combined_df.query(" and ".join(query_parts)) if query_parts else combined_df
        )
        return filtered_df.sort_values("sim_time").reset_index(drop=True)

    def list_federates(self) -> List[str]:
        """Provides a list of federates with data in the data backend

        Returns:
            List[str]: list of federates with data in the data backend
        """
        if not self.is_connected or not self.helper.analysis_path.exists():
            return []
        return sorted(
            [p.name for p in self.helper.analysis_path.iterdir() if p.is_dir()]
        )

    def list_data_types(self, federate_names: Optional[list[str]] = None) -> List[str]:
        """Provides a list of data types in data backend for a given federate

        Args:
            federate_names (str): name of federate whose available
                data types are being determined

        Returns:
            List[str]: list of data types in data backend
        """
        data_types = []
        if not self.is_connected:
            return data_types
        if federate_names is None:
            federate_names = self.list_federates()
        for federate_name in federate_names:
            federate_path = self.helper.analysis_path / federate_name
            if not federate_path.exists():
                continue
            data_types.extend(sorted([f.stem for f in federate_path.glob("*.csv")]))
        return sorted(data_types)

    def list_scenarios(self) -> List[str]:
        """Get list of unique scenarios in the data.

        Returns:
            List[str]: list of unique scenarios in the data
        """
        if not self._is_connected or not self.helper.analysis_path.exists():
            return []
        scenarios: set = set()
        for federate_path in self.helper.analysis_path.iterdir():
            if not federate_path.is_dir():
                continue
            for csv_file in federate_path.glob("*.csv"):
                if csv_file.stat().st_size > 0:
                    try:
                        df = pd.read_csv(csv_file, usecols=["scenario"])
                        scenarios.update(df["scenario"].unique())
                    except (KeyError, ValueError):
                        continue
        return sorted(list(scenarios))

    def get_time_range(self, **kwargs) -> Dict[str, float]:
        """Get the time range (min and max simulation times) for the data.

        Args:
            **kwargs (Dict[str, float]):

        Returns:
            Dict[str, float]: Dictionary with the time range for a given set of data.
                Returned dictionary is structured as::

                    {
                        "min_time": float value,
                        "max_time": float value
                    }

        """
        df = self.read_data(**kwargs)
        if df.empty:
            return {"min_time": 0.0, "max_time": 0.0}
        return {
            "min_time": float(df["sim_time"].min()),
            "max_time": float(df["sim_time"].max()),
        }


class CSVTimeSeriesManager(TSDataManager):
    """
    Joint CSV time-series manager using composition.
    Manages a shared Helper for a single reader and writer instance.
    """

    def __init__(self, *, location: str, analysis_name: str = "default", **kwargs):
        """Initialize CSV time-series manager."""
        super().__init__(**kwargs)
        # The manager creates ONE helper and shares it.
        self.helper: _CSVHelper = _CSVHelper(location, analysis_name)
        self.writer: CSVTimeSeriesWriter = CSVTimeSeriesWriter(helper=self.helper)
        self.reader: CSVTimeSeriesReader = CSVTimeSeriesReader(helper=self.helper)

    def connect(self) -> bool:
        """Establish connection for both reader and writer.

        Returns:
            bool: flag indicating whether the connection to the data backend
                exists
        """
        writer_connected = self.writer.connect()
        reader_connected = self.reader.connect()
        self._is_connected = writer_connected and reader_connected
        return self._is_connected

    def disconnect(self) -> None:
        """Close connection for both reader and writer.

        Returns:
            None
        """
        self.writer.disconnect()
        self.reader.disconnect()
        self._is_connected = False

    def list_federates(self) -> List[str]:
        """Lists federates with data in data backend

        Returns:
            List[str]: list of federates with data in data backend
        """
        return self.reader.list_federates()

    def list_data_types(self, federate_names: Optional[list[str]] = None) -> List[str]:
        """Lists data types for a given federate in the data backend

        Args:
            federate_names (str): Name of federate being queried

        Returns:
            List[str]: list of data types in data backend
        """
        return self.reader.list_data_types(federate_names)

    def list_scenarios(self) -> List[str]:
        """List of scenarios in the data backend

        Returns:
            List[str]: list of scenarios in the data backend
        """
        return self.reader.list_scenarios()

    def get_time_range(self, **kwargs) -> Dict[str, float]:
        """Get time range of data in data backend

        Args:
            **kwargs Dict[str, any]:

        Returns:
            Dict[str, float]: Dictionary with the time range for a given set of data.
                Returned dictionary is structured as::

                    {
                        "min_time": float value,
                        "max_time": float value
                    }

        """
        return self.reader.get_time_range(**kwargs)

    def delete_scenario_data(self, scenario_name: str) -> bool:
        """NOT IMPLEMENTED

        Delete data from the data backend for the specified scenario

        Args:
            scenario_name (str): Name of scenario being deleted

        Raises:
            NotImplementedError:

        Returns:
            bool: flag indicating whether data was deleted
        """
        raise NotImplementedError(
            "Scenario deletion is not efficiently supported for CSV files. "
            "Consider using a database backend for selective deletion."
        )

    def delete_federate_data(self, federate_name: str) -> bool:
        """Delete all data for a specific federate.

        Args:
            federate_name (str): federate for which to delete data

        Returns:
            bool: flag indicating whether data was deleted
        """
        try:
            validate_name(federate_name, context="federate")
            federate_path = self.helper.analysis_path / federate_name
            if federate_path.exists() and federate_path.is_dir():
                shutil.rmtree(federate_path)
                logger.debug(
                    f"Deleted all data for federate: {safe_name_log(federate_name)}"
                )
                return True
            else:
                logger.warning(
                    f"Federate directory not found: {safe_name_log(federate_name)}"
                )
                return False
        except (ValidationError, OSError) as e:
            logger.error(
                f"Failed to delete federate data for '{safe_name_log(federate_name)}': {e}"
            )
            return False

    def backup_analysis(self, backup_path: str) -> bool:
        """Create a backup of the entire analysis.

        Args:
            backup_path (str): path to back up data

        Returns:
            bool: flag indicating whether backup completed
        """
        if not self.helper.analysis_path.exists():
            logger.warning(
                f"Analysis '{self.analysis_name}' does not exist, nothing to backup"
            )
            return True
        try:
            backup_dest = Path(backup_path)
            shutil.copytree(self.helper.analysis_path, backup_dest, dirs_exist_ok=True)
            logger.info(f"Backed up analysis '{self.analysis_name}' to {backup_dest}")
            return True
        except Exception as e:
            logger.error(f"Failed to backup analysis '{self.analysis_name}': {e}")
            return False

    @property
    def location(self) -> Path:
        """Location property

        Returns:
            Path: location as a file path
        """
        return self.reader.helper.location

    @property
    def analysis_name(self) -> str:
        """Get the current analysis name.

        Returns:
            str: analysis name
        """
        return self.helper.analysis_name

    @analysis_name.setter
    def analysis_name(self, value: str) -> None:
        """Set the analysis name and update the shared helper.

        Args:
            value (str): name of analysis

        Returns:
            None
        """
        validate_name(value, context="analysis")
        self.helper.analysis_name = value
        self.helper.analysis_path = self.helper.location / value
