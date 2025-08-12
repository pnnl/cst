"""
CSV file-based time-series data management for CoSim Toolbox.
Refactored to use a composition-based architecture for clarity,
testability, and maintainability.
"""

import csv
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from .abstractions import (
    TSDataWriter,
    TSDataReader,
    TSDataManager,
    TSRecord,
)
from .validation import validate_name, ValidationError, safe_name_log

logger = logging.getLogger(__name__)


# +++ A dedicated helper class for shared CSV logic +++
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

    def __init__(self, location: str, analysis_name: str):
        validate_name(analysis_name, context="analysis")
        self.base_path = Path(location)
        self.analysis_name = analysis_name
        self.analysis_path = self.base_path / self.analysis_name

    def get_file_path(self, federate_name: str, data_type: str) -> Path:
        """Get the file path for a specific federate and data type."""
        federate_path = self.analysis_path / federate_name
        return federate_path / f"{data_type}.csv"

    def get_data_type(self, value: Any) -> str:
        """Determine the CST data type for a given value."""
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

    def format_value_for_csv(self, value: Any) -> str:
        """Format a value for CSV storage."""
        if isinstance(value, (list, tuple)):
            return json.dumps(value)
        if isinstance(value, complex):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    def parse_value_from_csv(self, value_str: str, data_type: str) -> Any:
        """Parse a value from CSV string back to appropriate Python type."""
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


# +++ Uses composition ("has-a" helper) instead of inheritance +++
class CSVTimeSeriesWriter(TSDataWriter):
    """CSV file-based time-series data writer."""

    def __init__(
        self,
        *,
        location: Optional[str] = None,
        analysis_name: str = "default",
        helper: Optional[_CSVHelper] = None,
    ):
        """
        Initialize the CSV writer.

        For standalone use:
            writer = CSVTimeSeriesWriter(location="/path/to/data", analysis_name="my_analysis")
        For managed use (by CSVTimeSeriesManager):
            helper = _CSVHelper(...)
            writer = CSVTimeSeriesWriter(helper=helper)
        """
        super().__init__()
        if helper:
            self.helper = helper
        elif location:
            self.helper = _CSVHelper(location, analysis_name)
        else:
            raise ValueError("Either 'helper' or 'location' must be provided.")

    def _ensure_file_exists(self, file_path: Path) -> None:
        """Ensure the CSV file exists with proper headers."""
        if not file_path.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(self.helper.CSV_HEADERS)

    def connect(self) -> bool:
        """Create directory structure if it doesn't exist."""
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
        except Exception as e:
            logger.error(f"Unexpected error connecting CSV writer: {e}")
            return False

    def disconnect(self) -> None:
        """Close connection (no-op for files, but maintains consistency)."""
        self._is_connected = False
        logger.debug("CSV time-series writer disconnected")

    def write_records(self, records: List[TSRecord]) -> bool:
        """Write TSRecord objects to CSV files."""
        if not self.is_connected:
            logger.error("CSV writer not connected. Call connect() first.")
            return False
        if not records:
            return True
        try:
            grouped_records: Dict[tuple[str, str], List[TSRecord]] = {}
            for record in records:
                validate_name(record.federate, context="federate")
                data_type = self.helper.get_data_type(record.data_value)
                key = (record.federate, data_type)
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
                            self.helper.format_value_for_csv(record.data_value),
                        ]
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
        if helper:
            self.helper = helper
        elif location:
            self.helper = _CSVHelper(location, analysis_name)
        else:
            raise ValueError("Either 'helper' or 'location' must be provided.")

    def connect(self) -> bool:
        """Verify that the directory structure exists."""
        if not self.helper.analysis_path.exists():
            logger.warning(f"Analysis path does not exist: {self.helper.analysis_path}")
        self._is_connected = True
        logger.info(f"CSV time-series reader connected to: {self.helper.analysis_path}")
        return True

    def disconnect(self) -> None:
        """Close connection (no-op for files)."""
        self._is_connected = False
        logger.debug("CSV time-series reader disconnected")

    def read_data(
        self,
        start_time: Optional[float] = None,
        duration: Optional[float] = None,
        scenario_name: Optional[str] = None,
        federate_name: Optional[str] = None,
        data_name: Optional[str] = None,
        data_type: Optional[str] = None,
    ) -> pd.DataFrame:
        """Read time-series data from CSV files."""
        if not self.is_connected:
            logger.error("CSV reader not connected. Call connect() first.")
            return pd.DataFrame()

        if not self.helper.analysis_path.exists():
            return pd.DataFrame()

        all_dataframes = []
        federate_dirs = (
            [self.helper.analysis_path / federate_name]
            if federate_name
            else self.helper.analysis_path.iterdir()
        )

        for federate_path in federate_dirs:
            if not federate_path.is_dir():
                continue

            csv_files = (
                [federate_path / f"{data_type}.csv"]
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
        if scenario_name:
            query_parts.append(f"scenario == '{scenario_name}'")
        if federate_name:
            query_parts.append(f"federate == '{federate_name}'")
        if data_name:
            query_parts.append(f"data_name == '{data_name}'")
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
        if not self.is_connected or not self.helper.analysis_path.exists():
            return []
        return sorted(
            [p.name for p in self.helper.analysis_path.iterdir() if p.is_dir()]
        )

    def list_data_types(self, federate_name: str) -> List[str]:
        if not self.is_connected:
            return []
        federate_path = self.helper.analysis_path / federate_name
        if not federate_path.exists():
            return []
        return sorted([f.stem for f in federate_path.glob("*.csv")])

    def get_scenarios(self) -> List[str]:
        """Get list of unique scenarios in the data."""
        if not self._is_connected or not self.helper.analysis_path.exists():
            return []
        scenarios = set()
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
        """Get the time range (min and max simulation times) for the data."""
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

    def __init__(self, location: str, analysis_name: str = "default"):
        """Initialize CSV time-series manager."""
        super().__init__()
        # The manager creates ONE helper and shares it.
        self.helper = _CSVHelper(location, analysis_name)
        self.writer = CSVTimeSeriesWriter(helper=self.helper)
        self.reader = CSVTimeSeriesReader(helper=self.helper)

    def connect(self) -> bool:
        """Establish connection for both reader and writer."""
        writer_connected = self.writer.connect()
        reader_connected = self.reader.connect()
        self._is_connected = writer_connected and reader_connected
        return self._is_connected

    def disconnect(self) -> None:
        """Close connection for both reader and writer."""
        self.writer.disconnect()
        self.reader.disconnect()
        self._is_connected = False

    def list_federates(self) -> List[str]:
        return self.reader.list_federates()

    def list_data_types(self, federate_name: str) -> List[str]:
        return self.reader.list_data_types(federate_name)

    def get_scenarios(self) -> List[str]:
        return self.reader.get_scenarios()

    def get_time_range(self, **kwargs) -> Dict[str, float]:
        return self.reader.get_time_range(**kwargs)

    def delete_scenario_data(self, scenario_name: str) -> bool:
        raise NotImplementedError(
            "Scenario deletion is not efficiently supported for CSV files. "
            "Consider using a database backend for selective deletion."
        )

    def delete_federate_data(self, federate_name: str) -> bool:
        """Delete all data for a specific federate."""
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
        """Create a backup of the entire analysis."""
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
    def analysis_name(self) -> str:
        """Get the current analysis name."""
        return self.helper.analysis_name

    @analysis_name.setter
    def analysis_name(self, value: str) -> None:
        """Set the analysis name and update the shared helper."""
        validate_name(value, context="analysis")
        self.helper.analysis_name = value
        self.helper.analysis_path = self.helper.base_path / value
