import logging
import os
import time
import unittest

import cosim_toolbox as env
#from cosim_toolbox.sims import DBConfigs
#from cosim_toolbox.sims import DBResults
from cosim_toolbox.dbms import create_metadata_manager
from cosim_toolbox.dbms import create_timeseries_manager

import collections
collections.Callable = collections.abc.Callable
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)

START_TIME = 500
DURATION = 1000
END_TIME = START_TIME + DURATION

class TestSimpleFederation(unittest.TestCase):

    def setUp(self):
        self.tmgr = create_timeseries_manager("postgres", 'test_analysis')
        self.tmgr.connect()

        scenario = {
            "analysis": 'test_analysis',
            "federation": 'test_federation',
            "start_time": "2023-12-07T15:31:27",
            "stop_time": "2023-12-08T15:31:27",
            "docker": False
        }

        with create_metadata_manager(backend="mongo") as mgr:
            print(f"Writing configuration files to '{mgr.location}'...")
            mgr.write_scenario('test_scenario', scenario, overwrite=True)
            print("Configuration files written successfully.")


    def test_simple_federation_result(self):
        # Check federation complete
        self._check_complete(interval=10, timeout=10 * 60)
        self._verify_query(federate_name="Battery", data_name="current3", data_type="hdt_boolean")
        self._verify_query(federate_name="Battery", data_name="Battery/current", data_type="hdt_double")
        self._verify_query(federate_name="Battery", data_name="current4", data_type="hdt_string")

    def _verify_query(self, federate_name: str, data_name: str, data_type: str):
        df = self.tmgr.read_data(
            start_time=START_TIME,
            duration=DURATION,
            scenario_name="test_scenario",
            federate_name=federate_name,
            data_name=data_name,
            data_type=data_type,
        )

        self.assertGreaterEqual(len(df), 1, "DataFrame should have at least one row")
        self.assertGreaterEqual(df.iloc[0]['sim_time'], START_TIME, "First row sim_time should be >= 500")
        self.assertLessEqual(df.iloc[-1]['sim_time'], END_TIME, "Last row sim_time should be <= 1500")

    def _check_complete(self, interval: int, timeout: int):
        start_time = time.time()
        while True:
            logging.info(f"Checking test federation completion with internal: {interval}; timeout: {timeout}")
            df = self.tmgr.read_data(
                start_time=86400,
#                duration=0,
                scenario_name="test_scenario",
                federate_name="Battery",
                data_name="Battery/current5",
                data_type="hdt_complex",
            )
            if not df.empty:
                logging.info("Test federation completed")
                break
            if time.time() - start_time > timeout:
                raise ValueError(f"Polling timed out in {timeout} without receiving non-empty DataFrame.")
            logging.info(f"Test federation is still in progress. Waiting to retry in {interval}")
            time.sleep(interval)

    def tearDown(self):
        self.tmgr = None
