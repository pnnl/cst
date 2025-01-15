"""
Created on 12/14/2023

CST Federate class that defines the basic operations of
Python-based logger federate in CoSimulation Toolbox.

@author: Mitch Pelton, Fred Rutz
"""
import json
import sys
import time

from cosim_toolbox.federate import Federate
from cosim_toolbox.bench_profile import bench_profile

class CST_Time:
    def __init__(self):
        self.proc_time0 = 0
        self.wall_time0 = 0
        self.proc_time = 0
        self.wall_time = 0

    def timing(self, start_stop: bool):
        if start_stop:
            self.proc_time0 = time.perf_counter()
            self.wall_time0 = time.time()
        else:
            self.proc_time += time.perf_counter() - self.proc_time0
            self.wall_time += time.time() - self.wall_time0

@bench_profile
class CST_Federate(Federate):
    def __init__(self, fed_name="", use_mdb=True, use_pdb=True, **kwargs):
        self.tmp = 0.
        self.dummy = 0.
        super().__init__(fed_name, use_mdb=use_mdb, use_pdb=use_pdb, **kwargs)
        self.path_csv = "federate_outputs/"

    def update_internal_model(self):
        """
        This is entirely user-defined code and is intended to be defined by
        sub-classing and overloading.
        """
        if not self.debug:
            raise NotImplementedError("Subclass from Federate and write code to update internal model")

        for key in self.data_from_federation["inputs"]:
            key_string = key[key.index("/"):]
            data_name = self.federate_name + key_string
            if self.dummy != 0.:
                self.tmp = self.data_from_federation["inputs"][key]
            self.data_to_federation["publications"][data_name] = self.dummy + self.tmp

        for key in self.data_from_federation["endpoints"]:
            key_string = key[key.index("/"):]
            data_name = self.federate_name + key_string
            for _key in self.endpoints:
                if key in self.endpoints[_key]['destination']:
                    if self.dummy != 0.:
                        self.tmp = float(self.data_from_federation["endpoints"][key][0].data)
                    self.data_to_federation["endpoints"][data_name] = [f"{self.dummy + self.tmp}"]

        self.dummy += 1


if __name__ == "__main__":
    use_dbase = True
    if sys.argv.__len__() > 3:
        if sys.argv[3].lower() in ['false', '0', 'f', 'n', 'no', 'nope', 'nada', 'noway', 'uh-uh']:
            use_dbase = False
        # if sys.argv[3].lower() in ['true', '1', 't', 'y', 'yes', 'yep', 'yea', 'yeah', 'un-uh']:
        #     use_dbase = True

    t_ = CST_Time()
    t_.timing(True)
    test_fed = CST_Federate(sys.argv[1], use_mdb=use_dbase, use_pdb=use_dbase)
    test_fed.create_federate(sys.argv[2])
    test_fed.run_cosim_loop()
    test_fed.destroy_federate()
    t_.timing(False)

    result = {
        "process_time": t_.proc_time,
        "wall_time": t_.wall_time
    }
    with open(f"./federate_outputs/{test_fed.federate_name}_timing.json", "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    del test_fed
