
from cosim_toolbox.sims import FederateLogger

if __name__ == "__main__":

    test_fed = FederateLogger()
    test_fed.run("MyScenario",
                 use_meta_db = "json",
                 use_data_db = "csv"
                 )
