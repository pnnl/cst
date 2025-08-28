import sys
from cosim_toolbox.federateLogger import FederateLogger
from pathlib import Path

base_path = Path(__file__).parent
if __name__ == "__main__":
    metadata_location = base_path / "config"
    timeseries_location = base_path / "data"
    # metadata_location=Path(__file__).parent / "config"
    # timeseries_location=Path(__file__).parent / "data"

    test_fed = FederateLogger(
        "logger",
        use_mdb=False,
        use_pdb=False,
        metadata_location=metadata_location,
        timeseries_location=timeseries_location,
    )
    test_fed.run("MyScenario")


# datalog.main('FederateLogger', 'HelicsExampleDefaultSchema', 'HelicsExampleDefault')
