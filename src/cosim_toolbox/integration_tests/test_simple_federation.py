import logging
import os
import time
import unittest

import cosim_toolbox as env
from cosim_toolbox.dbConfigs import DBConfigs
from cosim_toolbox.dbResults import DBResults

import collections
collections.Callable = collections.abc.Callable
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)

START_TIME = 500
DURATION = 1000
END_TIME = START_TIME + DURATION

class TestSimpleFederation(unittest.TestCase):

    def setUp(self):
        self.logger_data = DBResults()
        self.db = DBConfigs(env.cst_mongo, env.cst_mongo_db)

        # this may fail if run/python/test_federation/runner.py not ran
        # integration_test.sh does run this in the pipeline
        scenario = self.db.scenario('test_schema',
                                    'test_federation',
                                    "2023-12-07T15:31:27",
                                    "2023-12-08T15:31:27",
                                    False)
        self.db.remove_document(env.cst_scenarios, None, 'test_scenario')
        self.db.add_dict(env.cst_scenarios, 'test_scenario', scenario)

    def test_simple_federation_result(self):
        self.logger_data.open_database_connections()

        # Check federation complete
        self._check_complete(interval=10, timeout=10 * 60)
        self._verify_query(federate_name="Battery", data_name="Battery/current3", data_type="hdt_boolean")
        self._verify_query(federate_name="Battery", data_name="Battery/current", data_type="hdt_double")
        self._verify_query(federate_name="EVehicle", data_name="EVehicle/voltage4", data_type="hdt_string")
        self.logger_data.close_database_connections()

    def _verify_query(self, federate_name: str, data_name: str, data_type: str):
        df = self.logger_data.query_scenario_federate_times(
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
            df = self.logger_data.query_scenario_federate_times(
                start_time=86400,
                duration=0,
                scenario_name="test_scenario",
                federate_name="EVehicle",
                data_name="EVehicle/voltage5",
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
        self.logger_data = None
        self.db = None