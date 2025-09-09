import logging
import os
import time
import unittest
import collections
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any

# --- NEW API Imports ---
from cosim_toolbox.dbms import create_metadata_manager, create_timeseries_manager

collections.Callable = collections.abc.Callable
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)

# --- Test Constants ---
START_TIME = 500
DURATION = 1000
END_TIME = START_TIME + DURATION
SCENARIO_NAME = "test_scenario"
ANALYSIS_NAME = "test_analysis"
FEDERATION_NAME = "test_federation"

# --- Centralized Configuration for File-Based Backends ---
# These will be updated in setUp to point to a temporary directory
METADATA_CONFIG = {"backend": "json"}
TIMESERIES_CONFIG = {"backend": "csv"}


def _create_test_scenario_doc() -> Dict[str, Any]:
    """Helper function to create a consistent test scenario document."""
    return {
        "analysis": ANALYSIS_NAME,
        "federation": FEDERATION_NAME,
        "start_time": "2023-12-07T15:31:27",
        "stop_time": "2023-12-08T15:31:27",
        "docker": False,
    }


def _create_mock_federation_doc() -> Dict[str, Any]:
    """Helper to create a mock federation file needed by the test scenario."""
    # This mock only needs to contain the federates mentioned in the test queries.
    return {
        "federation": {
            "Battery": {
                # Dummy content, as it's not directly used by the test itself
                "HELICS_config": {}
            },
            "EVehicle": {"HELICS_config": {}},
        }
    }


class TestSimpleFederation(unittest.TestCase):
    def setUp(self):
        """Set up a temporary directory for all test inputs and outputs."""
        logger.info("Setting up test case: TestSimpleFederation")

        # 1. Create a temporary directory for this test run
        self.temp_dir = tempfile.mkdtemp(prefix="copper_test_")
        logger.info(f"Created temporary directory: {self.temp_dir}")

        # 2. Define paths for metadata and timeseries within the temp directory
        self.metadata_path = Path(self.temp_dir) / "config"
        self.timeseries_path = Path(self.temp_dir) / "timeseries"
        self.metadata_path.mkdir()
        self.timeseries_path.mkdir()

        # 3. Update the backend configs to use the temporary paths
        self.metadata_config = {**METADATA_CONFIG, "location": str(self.metadata_path)}
        self.timeseries_config = {
            **TIMESERIES_CONFIG,
            "location": str(self.timeseries_path),
        }

        # 4. Pre-populate the necessary configuration files
        try:
            with create_metadata_manager(**self.metadata_config) as mgr:
                # Write the mock federation file that the scenario depends on
                fed_doc = _create_mock_federation_doc()
                mgr.write_federation(FEDERATION_NAME, fed_doc)

                # Write the test scenario file
                scenario_doc = _create_test_scenario_doc()
                mgr.write_scenario(SCENARIO_NAME, scenario_doc)
            logger.info(f"Test config files written to '{self.metadata_path}'")
        except Exception as e:
            self.fail(f"Failed to set up mock configuration files: {e}")

        # 5. Instantiate the TimeSeriesManager
        try:
            self.timeseries_manager = create_timeseries_manager(
                analysis_name=ANALYSIS_NAME, **self.timeseries_config
            )
            logger.info("CSV TimeSeriesManager created successfully.")
        except Exception as e:
            self.fail(f"Failed to set up CSV timeseries manager: {e}")

    def test_simple_federation_result(self):
        """
        Main test method. Polls for completion and verifies specific data points.

        NOTE: This test now relies on an external process (the co-simulation run)
        to populate the temporary timeseries directory with CSV files.
        """
        self._check_complete(interval=10, timeout=10 * 60)
        self._verify_query(
            federate_name="Battery", data_name="Battery/current3", data_type="boolean"
        )
        self._verify_query(
            federate_name="Battery", data_name="Battery/current", data_type="double"
        )
        self._verify_query(
            federate_name="EVehicle", data_name="EVehicle/voltage4", data_type="string"
        )

    def _verify_query(self, federate_name: str, data_name: str, data_type: str):
        """Helper to query for data and assert its validity."""
        logger.info(
            f"Verifying data for: federate='{federate_name}', data='{data_name}'"
        )

        # For CSV backend, all data is loaded and then filtered.
        df = self.timeseries_manager.read_data(
            start_time=START_TIME,
            duration=DURATION,
            scenario_name=SCENARIO_NAME,
            federate_name=federate_name,
            data_name=data_name,
            data_type=data_type.replace("hdt_", ""),
        )

        self.assertIsNotNone(df, "read_data should not return None")
        self.assertFalse(df.empty, f"DataFrame should not be empty for {data_name}")
        self.assertGreaterEqual(len(df), 1, "DataFrame should have at least one row")
        self.assertGreaterEqual(
            df.iloc[0]["sim_time"],
            START_TIME,
            "First row sim_time should be >= start time",
        )
        self.assertLessEqual(
            df.iloc[-1]["sim_time"], END_TIME, "Last row sim_time should be <= end time"
        )

    def _check_complete(self, interval: int, timeout: int):
        """Polls the filesystem for a signal file indicating the simulation has finished."""
        start_time = time.time()
        while True:
            logger.info(f"Checking for federation completion signal...")

            # For a file-based system, we poll for the existence of the expected result files.
            df = self.timeseries_manager.read_data(
                start_time=86400,
                duration=86400,
                scenario_name=SCENARIO_NAME,
                federate_name="EVehicle",
                data_name="EVehicle/voltage5",
                data_type="complex",
            )

            if df is not None and not df.empty:
                logger.info("Test federation completion signal found in CSV files.")
                break

            if time.time() - start_time > timeout:
                self.fail(
                    f"Polling timed out in {timeout} seconds without finding completion signal in CSV files."
                )

            logger.info(f"Signal not found. Retrying in {interval} seconds...")
            time.sleep(interval)

    def tearDown(self):
        """Clean up by removing the temporary directory."""
        logger.info("Tearing down test case: TestSimpleFederation")
        if self.timeseries_manager and hasattr(self.timeseries_manager, "disconnect"):
            self.timeseries_manager.disconnect()  # Good practice, even if it does nothing for CSV

        try:
            shutil.rmtree(self.temp_dir)
            logger.info(f"Removed temporary directory: {self.temp_dir}")
        except Exception as e:
            logger.error(f"Error removing temporary directory {self.temp_dir}: {e}")
