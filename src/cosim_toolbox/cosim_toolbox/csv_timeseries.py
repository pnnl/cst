"""
CSV file-based time-series data management for CoSim Toolbox.
Provides CSV file storage for time-series data using TSRecord structure.
Refactored to use composition-based approach with separate reader/writer classes.
@author: [AUTHOR]
"""

import csv
import logging
import pandas as pd
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
import re

from .data_management import (
    TSDataWriter,
    TSDataReader,
    TSDataManager,
    TSRecord,
    ConnectionInfo,
)

logger = logging.getLogger(__name__)


class CSVTimeSeriesWriter(TSDataWriter):
    """
    CSV file-based time-series data writer.
    Writes time-series data as CSV files in a structured folder hierarchy.
    """

    # Map Python types to CST data type names
    TYPE_MAPPING = {
        float: "hdt_double",
        int: "hdt_integer",
        str: "hdt_string",
        bool: "hdt_boolean",
        complex: "hdt_complex",
        list: "hdt_vector",
    }

    # CSV headers matching TSRecord structure
    CSV_HEADERS = [
        "real_time",
        "sim_time",
        "scenario",
        "federate",
        "data_name",
        "data_value",
    ]

    def __init__(self, connection_info: ConnectionInfo):
        """
        Initialize CSV time-series writer.
        Args:
            connection_info: Dict containing 'base_path', 'analysis_path', 'analysis_name'
        """
        super().__init__(connection_info)
        self.base_path = connection_info["base_path"]
        self.analysis_path = connection_info["analysis_path"]
        self.analysis_name = connection_info["analysis_name"]

    def _validate_name(self, name: str) -> None:
        """Validate that a name is safe for filesystem use."""
        if not name or len(name) > 255:
            raise ValueError(f"Name invalid (empty or >255 chars): {name}")
        # Basic filesystem safety check
        if re.search(r'[<>:"/\\|?*\x00-\x1f]', name):
            raise ValueError(f"Name contains invalid characters: {name}")
        if name.startswith((" ", ".")) or name.endswith((" ", ".")):
            raise ValueError(f"Name has invalid format: {name}")

    def _get_data_type(self, value: Any) -> str:
        """
        Determine the CST data type for a given value.
        Args:
            value: The data value to classify
        Returns:
            str: CST data type name (e.g., 'hdt_double', 'hdt_string')
        """
        if isinstance(value, bool):  # Check bool before int (bool is subclass of int)
            return "hdt_boolean"
        elif isinstance(value, int):
            return "hdt_integer"
        elif isinstance(value, float):
            return "hdt_double"
        elif isinstance(value, complex):
            return "hdt_complex"
        elif isinstance(value, str):
            return "hdt_string"
        elif isinstance(value, (list, tuple)):
            # Check if it's a complex vector
            if value and isinstance(value[0], complex):
                return "hdt_complex_vector"
            else:
                return "hdt_vector"
        else:
            # Default to string representation for unknown types
            return "hdt_string"

    def _get_file_path(self, federate_name: str, data_type: str) -> Path:
        """
        Get the file path for a specific federate and data type.
        Args:
            federate_name (str): Name of the federate
            data_type (str): CST data type
        Returns:
            Path: Path to the CSV file
        """
        federate_path = self.analysis_path / federate_name
        return federate_path / f"{data_type}.csv"

    def _ensure_file_exists(self, file_path: Path) -> None:
        """
        Ensure the CSV file exists with proper headers.
        Args:
            file_path (Path): Path to the CSV file
        """
        if not file_path.exists():
            # Create directory if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)
            # Create file with headers
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(self.CSV_HEADERS)

    def _format_value_for_csv(self, value: Any) -> str:
        """
        Format a value for CSV storage.
        Args:
            value: The value to format
        Returns:
            str: Formatted value suitable for CSV
        """
        if isinstance(value, (list, tuple)):
            # Convert lists/tuples to string representation
            return str(value)
        elif isinstance(value, complex):
            # Store complex numbers as string
            return str(value)
        elif isinstance(value, datetime):
            # Store datetime as ISO format string
            return value.isoformat()
        else:
            return str(value)

    def connect(self) -> bool:
        """
        Create directory structure if it doesn't exist.
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            self.analysis_path.mkdir(parents=True, exist_ok=True)
            self._is_connected = True
            logger.info(
                f"CSV time-series writer connected to: {self.base_path}/{self.analysis_name}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to connect CSV writer: {e}")
            return False

    def disconnect(self) -> None:
        """
        Close connection (no-op for files, but maintain consistency).
        """
        self._is_connected = False
        logger.debug("CSV time-series writer disconnected")

    def write_records(self, records: List[TSRecord]) -> bool:
        """
        Write TSRecord objects to CSV files.
        Args:
            records (List[TSRecord]): List of time-series records to write
        Returns:
            bool: True if write successful, False otherwise
        """
        if not self._is_connected:
            logger.error("CSV writer not connected")
            return False

        if not records:
            return True

        try:
            # Group records by federate and data type
            grouped_records = {}
            for record in records:
                self._validate_name(record.federate)
                data_type = self._get_data_type(record.data_value)
                key = (record.federate, data_type)
                if key not in grouped_records:
                    grouped_records[key] = []
                grouped_records[key].append(record)

            # Write each group to its respective file
            for (federate_name, data_type), group_records in grouped_records.items():
                file_path = self._get_file_path(federate_name, data_type)
                self._ensure_file_exists(file_path)

                # Append records to file
                with open(file_path, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    for record in group_records:
                        row = [
                            record.real_time.isoformat(),
                            record.sim_time,
                            record.scenario,
                            record.federate,
                            record.data_name,
                            self._format_value_for_csv(record.data_value),
                        ]
                        writer.writerow(row)

            logger.debug(f"Wrote {len(records)} records to CSV files")
            return True

        except Exception as e:
            logger.error(f"Failed to write records to CSV: {e}")
            return False

    # Add context manager support to individual reader/writer classes
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


class CSVTimeSeriesReader(TSDataReader):
    """
    CSV file-based time-series data reader.
    Reads time-series data from CSV files in structured folder hierarchy.
    """

    def __init__(self, connection_info: ConnectionInfo):
        """
        Initialize CSV time-series reader.
        Args:
            connection_info: Dict containing 'base_path', 'analysis_path', 'analysis_name'
        """
        super().__init__(connection_info)
        self.base_path = connection_info["base_path"]
        self.analysis_path = connection_info["analysis_path"]
        self.analysis_name = connection_info["analysis_name"]

    def _parse_value_from_csv(self, value_str: str, data_type: str) -> Any:
        """
        Parse a value from CSV string back to appropriate Python type.
        Args:
            value_str (str): String value from CSV
            data_type (str): CST data type
        Returns:
            Any: Parsed value in appropriate Python type
        """
        if data_type == "hdt_double":
            return float(value_str)
        elif data_type == "hdt_integer":
            return int(value_str)
        elif data_type == "hdt_boolean":
            return value_str.lower() in ("true", "1", "yes")
        elif data_type == "hdt_complex":
            return complex(value_str)
        elif data_type in ("hdt_vector", "hdt_complex_vector"):
            # Parse list representation
            import ast

            return ast.literal_eval(value_str)
        else:
            return value_str  # Keep as string

    def connect(self) -> bool:
        """
        Verify that the directory structure exists.
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.analysis_path.exists():
                logger.warning(f"Analysis path does not exist: {self.analysis_path}")
                # Don't fail - directory might be created later by writer

            self._is_connected = True
            logger.info(
                f"CSV time-series reader connected to: {self.base_path}/{self.analysis_name}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to connect CSV reader: {e}")
            return False

    def disconnect(self) -> None:
        """
        Close connection (no-op for files).
        """
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
        """
        Read time-series data from CSV files.
        Args:
            start_time (Optional[float]): Starting time for data query
            duration (Optional[float]): Duration in seconds for data query
            scenario_name (Optional[str]): Filter by scenario name
            federate_name (Optional[str]): Filter by federate name
            data_name (Optional[str]): Filter by data name
            data_type (Optional[str]): Filter by specific data type
        Returns:
            pd.DataFrame: Time-series data as a Pandas DataFrame
        """
        if not self._is_connected:
            logger.error("CSV reader not connected")
            return pd.DataFrame()

        try:
            all_data = []

            # Determine which directories to read from
            if federate_name:
                # Read from specific federate
                federate_paths = [self.analysis_path / federate_name]
            else:
                # Read from all federates
                if not self.analysis_path.exists():
                    return pd.DataFrame()
                federate_paths = [p for p in self.analysis_path.iterdir() if p.is_dir()]

            for federate_path in federate_paths:
                if not federate_path.exists():
                    continue

                # Determine which data type files to read
                if data_type:
                    csv_files = [federate_path / f"{data_type}.csv"]
                else:
                    csv_files = list(federate_path.glob("*.csv"))

                for csv_file in csv_files:
                    if not csv_file.exists():
                        continue

                    # Read CSV file
                    try:
                        df = pd.read_csv(csv_file)
                        if df.empty:
                            continue

                        # Parse data types appropriately
                        current_data_type = (
                            csv_file.stem
                        )  # Get filename without extension
                        if "data_value" in df.columns:
                            df["data_value"] = df["data_value"].apply(
                                lambda x: self._parse_value_from_csv(
                                    str(x), current_data_type
                                )
                            )

                        # Convert real_time back to datetime
                        if "real_time" in df.columns:
                            df["real_time"] = pd.to_datetime(df["real_time"])

                        all_data.append(df)

                    except Exception as e:
                        logger.warning(f"Failed to read CSV file {csv_file}: {e}")
                        continue

            if not all_data:
                return pd.DataFrame()

            # Combine all data
            combined_df = pd.concat(all_data, ignore_index=True)

            # Apply filters
            filtered_df = combined_df
            if scenario_name:
                filtered_df = filtered_df[filtered_df["scenario"] == scenario_name]
            if federate_name:
                filtered_df = filtered_df[filtered_df["federate"] == federate_name]
            if data_name:
                filtered_df = filtered_df[filtered_df["data_name"] == data_name]

            # Apply time filters
            if start_time is not None:
                filtered_df = filtered_df[filtered_df["sim_time"] >= start_time]
            if duration is not None and start_time is not None:
                end_time = start_time + duration
                filtered_df = filtered_df[filtered_df["sim_time"] < end_time]
            elif duration is not None:
                filtered_df = filtered_df[filtered_df["sim_time"] < duration]

            # Sort by simulation time
            if not filtered_df.empty:
                filtered_df = filtered_df.sort_values("sim_time").reset_index(drop=True)

            logger.debug(f"Read {len(filtered_df)} records from CSV files")
            return filtered_df

        except Exception as e:
            logger.error(f"Failed to read data from CSV: {e}")
            return pd.DataFrame()

    # Utility methods for the reader
    def list_federates(self) -> List[str]:
        """
        List available federates in the analysis.
        Returns:
            List[str]: List of federate names
        """
        if not self._is_connected or not self.analysis_path.exists():
            return []

        try:
            federates = []
            for path in self.analysis_path.iterdir():
                if path.is_dir():
                    federates.append(path.name)
            return sorted(federates)
        except Exception as e:
            logger.error(f"Failed to list federates: {e}")
            return []

    def list_data_types(self, federate_name: str) -> List[str]:
        """
        List available data types for a specific federate.
        Args:
            federate_name (str): Name of the federate
        Returns:
            List[str]: List of data type names
        """
        if not self._is_connected:
            return []

        try:
            federate_path = self.analysis_path / federate_name
            if not federate_path.exists():
                return []

            data_types = []
            for csv_file in federate_path.glob("*.csv"):
                data_types.append(csv_file.stem)
            return sorted(data_types)
        except Exception as e:
            logger.error(f"Failed to list data types for {federate_name}: {e}")
            return []

    def get_scenarios(self) -> List[str]:
        """
        Get list of unique scenarios in the data.
        Returns:
            List[str]: List of scenario names
        """
        if not self._is_connected or not self.analysis_path.exists():
            return []

        try:
            scenarios = set()
            for federate_path in self.analysis_path.iterdir():
                if not federate_path.is_dir():
                    continue
                for csv_file in federate_path.glob("*.csv"):
                    if csv_file.stat().st_size > 0:  # Only check non-empty files
                        try:
                            df = pd.read_csv(
                                csv_file, nrows=100
                            )  # Sample first 100 rows
                            if "scenario" in df.columns:
                                scenarios.update(df["scenario"].unique())
                        except Exception:
                            continue  # Skip problematic files
            return sorted(list(scenarios))
        except Exception as e:
            logger.error(f"Failed to get scenarios: {e}")
            return []

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
        df = self.read_data(scenario_name=scenario_name, federate_name=federate_name)
        if df.empty:
            return {"min_time": 0.0, "max_time": 0.0}
        return {
            "min_time": float(df["sim_time"].min()),
            "max_time": float(df["sim_time"].max()),
        }

    # Add context manager support
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


class CSVTimeSeriesManager(TSDataManager):
    """
    Joint CSV time-series manager using composition.
    Combines separate reader and writer instances that share connection information.
    """

    def __init__(self, location: str, analysis_name: str = "default"):
        """
        Initialize CSV time-series manager.
        Args:
            location (str): Base directory path for CSV file storage
            analysis_name (str): Analysis name for organizing data
        """
        # Store analysis_name before calling super().__init__
        self._analysis_name = analysis_name
        super().__init__(location, analysis_name=analysis_name)

    def _create_connection_info(self, location: str, **kwargs) -> ConnectionInfo:
        """Create shared connection info for CSV storage."""
        analysis_name = kwargs.get("analysis_name", "default")
        base_path = Path(location)
        analysis_path = base_path / analysis_name

        return {
            "base_path": base_path,
            "analysis_path": analysis_path,
            "analysis_name": analysis_name,
        }

    def _create_writer(self, connection_info: ConnectionInfo) -> TSDataWriter:
        """Create CSV writer with shared connection info."""
        return CSVTimeSeriesWriter(connection_info)

    def _create_reader(self, connection_info: ConnectionInfo) -> TSDataReader:
        """Create CSV reader with shared connection info."""
        return CSVTimeSeriesReader(connection_info)

    # Override read_data to support data_type parameter explicitly
    def read_data(
        self,
        start_time: Optional[float] = None,
        duration: Optional[float] = None,
        scenario_name: Optional[str] = None,
        federate_name: Optional[str] = None,
        data_name: Optional[str] = None,
        data_type: Optional[str] = None,  # CSV-specific parameter
    ) -> pd.DataFrame:
        """Read time-series data from CSV files."""
        return self.reader.read_data(
            start_time=start_time,
            duration=duration,
            scenario_name=scenario_name,
            federate_name=federate_name,
            data_name=data_name,
            data_type=data_type,
        )

    # Expose utility methods from reader
    def list_federates(self) -> List[str]:
        """List available federates in the analysis."""
        return self.reader.list_federates()

    def list_data_types(self, federate_name: str) -> List[str]:
        """List available data types for a specific federate."""
        return self.reader.list_data_types(federate_name)

    def get_scenarios(self) -> List[str]:
        """Get list of unique scenarios in the data."""
        return self.reader.get_scenarios()

    def get_time_range(
        self, scenario_name: Optional[str] = None, federate_name: Optional[str] = None
    ) -> Dict[str, float]:
        """Get the time range for the data."""
        return self.reader.get_time_range(scenario_name, federate_name)

    def delete_federate_data(self, federate_name: str) -> bool:
        """
        Delete all data for a specific federate.
        Args:
            federate_name (str): Name of the federate
        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            # Validate name using writer's validation
            self.writer._validate_name(federate_name)
            federate_path = self.connection_info["analysis_path"] / federate_name
            if federate_path.exists():
                import shutil

                shutil.rmtree(federate_path)
                logger.debug(f"Deleted all data for federate: {federate_name}")
                return True
            else:
                logger.warning(f"Federate directory not found: {federate_name}")
                return False
        except Exception as e:
            logger.error(f"Failed to delete federate data: {e}")
            return False

    def delete_scenario_data(self, scenario_name: str) -> bool:
        """
        Delete all data for a specific scenario across all federates.
        Args:
            scenario_name (str): Name of the scenario
        Returns:
            bool: True if deletion successful, False otherwise
        """
        # Always raise NotImplementedError immediately
        raise NotImplementedError(
            "Scenario deletion is not efficiently supported for CSV files. "
            "Consider using database backends (MongoDB/PostgreSQL) for selective deletion."
        )

    @property
    def analysis_name(self) -> str:
        """Get the current analysis name."""
        return self._analysis_name

    @analysis_name.setter
    def analysis_name(self, value: str) -> None:
        """Set the analysis name and update connection info."""
        self._analysis_name = value
        # Update the shared connection info
        self.connection_info["analysis_name"] = value
        self.connection_info["analysis_path"] = (
            self.connection_info["base_path"] / value
        )
        # Update reader and writer analysis names
        self.writer.analysis_name = value
        self.reader.analysis_name = value
        self.writer.analysis_path = self.connection_info["analysis_path"]
        self.reader.analysis_path = self.connection_info["analysis_path"]
