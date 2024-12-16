from glmpy import Gridlabd
from pathlib import Path
import json
import logging
from cosim_toolbox.readConfig import ReadConfig

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)


class FederateGridlabD:
    def __init__(self, fed_name="", **kwargs):
        self.config: dict = None
        self.scenario: ReadConfig = None
        self.scenario_name: str = None
        self.federate: dict = None
        self.federate_type: str = None
        self.federate_name: str = fed_name
        self.start: float = None
        self.stop: float = None
        self.time_step = -1.0
        self.stop_time = -1.0
        self.granted_time = -1.0
        self.next_requested_time = -1.0
        self.pubs = {}
        self.inputs = {}
        self.endpoints = {}
        self.debug = True
        self.glm = None

        # if not wanting to debug, add debug=False as an argument
        self.__dict__.update(kwargs)

    def create_federate(self, scenario_name: str) -> None:
        """Create GridLAB-D Federate

        """
        if scenario_name is None:
            raise NameError("scenario_name is None")
        self.scenario_name = scenario_name
        self.scenario = ReadConfig(scenario_name)

        self.federate = self.scenario.federation["federation"][self.federate_name]
        self.federate_type = self.federate["federate_type"]
        # self.time_step = self.federate["time_step"]
        self.time_step = self.federate["HELICS_config"].get("period")
        self.config = self.federate["HELICS_config"]
        self.model_path = self.federate.get("model_path", "system.glm")

        model_path = Path(self.model_path)
        glm = Gridlabd(model_path)
        glm.remove_quotes_from_obj_names()  # clean object names
        glm.remove_outputs()
        glm.clock["starttime"] = "'" + str(self.scenario.start_time).replace("T", " ") + "'"
        glm.clock["stoptime"] =  "'" + str(self.scenario.stop_time).replace("T", " ") + "'"
        self.glm = glm



    def run(self, scenario_name):
        self.create_federate(scenario_name)
        self.glm.run(helics_config=self.config)
        # self.glm.run(tmp_dir_path=Path("../gld_tmp/").resolve())

if __name__ == '__main__':
    gld = FederateGridlabD(fed_name="gld")
    gld.run(scenario_name="gld1")
