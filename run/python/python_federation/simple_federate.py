"""
Created on 12/14/2023

Data logger class that defines the basic operations of Python-based logger federate in
Copper.

@author:
mitch.pelton@pnnl.gov
"""

import sys
from pathlib import Path
from cosim_toolbox.federate import Federate


class SimpleFederate(Federate):
    def __init__(self, fed_name="", schema="default", **kwargs):
        self.dummy = 0
        super().__init__(fed_name, **kwargs)

    def update_internal_model(self):
        """
        This is entirely user-defined code and is intended to be defined by
        sub-classing and overloading.
        """
        if not self.debug:
            raise NotImplementedError(
                "Subclass from Federate and write code to update internal model"
            )

        for key in self.data_from_federation["inputs"]:
            print(self.data_from_federation["inputs"][key])
            self.dummy += 1

        # Send out incremented value on arbitrary publication
        # Clear out values published last time
        for key in self.data_to_federation["publications"]:
            self.data_to_federation["publications"][key] = None
        for key in self.data_to_federation["endpoints"]:
            self.data_to_federation["endpoints"][key] = None

        for key in self.data_to_federation["publications"]:
            self.data_to_federation["publications"][key] = self.dummy + 1


if __name__ == "__main__":
    metadata_location="penny.pnl.gov"
    timeseries_location="penny.pnl.gov"
    # metadata_location=Path(__file__).parent / "config"
    # timeseries_location=Path(__file__).parent / "data"
    if sys.argv.__len__() > 2:
        test_fed = SimpleFederate(
            sys.argv[1],
            use_mdb=True,
            use_pdb=True,
            metadata_location=metadata_location,
            timeseries_location=timeseries_location,
        )
        test_fed.run(sys.argv[2])
