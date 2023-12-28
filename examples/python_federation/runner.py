import os
import sys
from pathlib import Path

sys.path.insert(1, os.path.join(Path(__file__).parent, '..', '..', 'src'))
import metadataDB as mDB
from Federate import Federate
from helics_messages import HelicsMsg


class Runner():

    def __init__(self):
        self.db = mDB.MetaDB(mDB.cu_uri, mDB.cu_database)

    def define_scenario(self, scenario_name):
        names = ["Battery", "EVehicle"]
        t1 = HelicsMsg(names[0], 30)
        t1.config("core_type", "zmq")
        t1.config("log_level", "warning")
        t1.config("period", 60)
        t1.config("uninterruptible", False)
        t1.config("terminate_on_error", True)
        t1.config("wait_for_current_time_update", True)
        t1.pubs_e(True, names[0] + "/EV1_current", "double", "A")
        t1.subs_e(True, names[1] + "/EV1_voltage", "double", "V")
        t1 = {
            "image": "tesp-tespapi:latest",
            "command": "exec python3 simple_federate.py " + names[0] + " " + scenario_name,
            "federate_type": "value",
            "time_step": 120,
            "HELICS_config": t1.write_json()
        }

        t2 = HelicsMsg(names[1], 30)
        t2.config("core_type", "zmq")
        t2.config("log_level", "warning")
        t2.config("period", 60)
        t2.config("uninterruptible", False)
        t2.config("terminate_on_error", True)
        t2.config("wait_for_current_time_update", True)
        t2.subs_e(True, names[0] + "/EV1_current", "double", "A")
        t2.pubs_e(True, names[1] + "/EV1_voltage", "double", "V")
        t2 = {
            "image": "tesp-tespapi:latest",
            "command": "exec python3 simple_federate.py " + names[1] + " " + scenario_name,
            "env": "",
            "federate_type": "value",
            "time_step": 120,
            "HELICS_config": t2.write_json()
        }
        diction = {
            "federation": {
                names[0]: t1,
                names[1]: t2
            }
        }

        federation_name = "MyBT1_EV1"
        print(mDB.cu_federations, self.db.get_collection_document_names(mDB.cu_federations))
        self.db.remove_document(mDB.cu_federations, None, federation_name)
        print(mDB.cu_federations, self.db.get_collection_document_names(mDB.cu_federations))
        self.db.add_dict(mDB.cu_federations, federation_name, diction)

        scenario = mDB.scenario_tojson(federation_name, "2023-12-07T15:31:27", "2023-12-08T15:31:27")
        print(mDB.cu_scenarios, self.db.get_collection_document_names(mDB.cu_scenarios))
        self.db.remove_document(mDB.cu_scenarios, None, scenario_name)
        print(mDB.cu_scenarios, self.db.get_collection_document_names(mDB.cu_scenarios))
        self.db.add_dict(mDB.cu_scenarios, scenario_name, scenario)


if __name__ == "__main__":
    r = Runner()
    my_scenario_name = "MyTest"
    r.define_scenario(my_scenario_name)
    mDB.define_yaml(my_scenario_name)
