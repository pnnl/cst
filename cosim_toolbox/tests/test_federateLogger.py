import collections
collections.Callable = collections.abc.Callable

import unittest

from cosim_toolbox.sims import FederateLogger


class TestFederateLogger(unittest.TestCase):

    def setUp(self):
        # Mocking HelicsMsg and Federate to isolate the tests
        self.federateLogger = FederateLogger(fed_name="TestFederate", analysis_name="TestAnalysis")

    # Add more tests for other methods as needed

    def tearDown(self):
        self.federateLogger = None


if __name__ == '__main__':
    unittest.main()
