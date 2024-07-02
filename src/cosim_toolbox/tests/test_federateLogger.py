import collections
collections.Callable = collections.abc.Callable

import unittest

from cosim_toolbox.federateLogger import FederateLogger


class TestFederateLogger(unittest.TestCase):

    def setUp(self):
        # Mocking HelicsMsg and Federate to isolate the tests
        self.federateLogger = FederateLogger(fed_name="TestFederate", schema_name="TestSchema")

    # Add more tests for other methods as needed

    def tearDown(self):
        self.federateLogger = None


if __name__ == '__main__':
    unittest.main()
