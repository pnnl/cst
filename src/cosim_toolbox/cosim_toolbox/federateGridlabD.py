from glmpy import Gridlabd
from pathlib import Path
import logging
from typing import Optional, Dict, Any
from data_management.factories import create_metadata_manager

logger = logging.getLogger(__name__)

class FederateGridlabD:
    """
    A launcher class for creating and running a GridLAB-D federate.

    This class reads co-simulation configuration from a specified backend,
    prepares a GridLAB-D model, and then executes it as a HELICS federate.
    It does not run a Python-based HELICS loop itself.
    """

    def __init__(
        self,
        fed_name: str,
        backend: str = "json",
        **backend_config
    ):
        """
        Initializes the GridLAB-D federate launcher.

        Args:
            fed_name (str): The name of the GridLAB-D federate as defined
                            in the federation configuration.
            backend (str, optional): The data_management backend to use
                ('json', 'mongo', etc.). Defaults to "json".
            **backend_config: Keyword arguments required by the chosen
                backend's metadata manager.
                - For 'json': `location='./config'`
                - For 'mongo': `location`, `database`, `user`, `password`, etc.
        """
        self.federate_name: str = fed_name
        self.backend: str = backend
        self.backend_config: Dict[str, Any] = backend_config
        self.config: Optional[Dict[str, Any]] = None
        self.federate: Optional[Dict[str, Any]] = None
        self.model_path: Optional[str] = None
        self.glm: Optional[Gridlabd] = None

    def create_federate(self, scenario_name: str) -> None:
        """
        Loads configuration and prepares the GridLAB-D model for execution.

        Args:
            scenario_name (str): The name of the scenario to run.

        Raises:
            NameError: If scenario_name is None.
            ValueError: If scenario or federation documents cannot be found.
        """
        if scenario_name is None:
            raise NameError("scenario_name is None")

        logger.info(f"Loading configuration for scenario '{scenario_name}' from '{self.backend}' backend...")

        try:
            with create_metadata_manager(backend=self.backend, **self.backend_config) as mgr:
                logger.info(f"Successfully connected to '{self.backend}' backend.")
                
                scenario_doc = mgr.read_scenario(scenario_name)
                if not scenario_doc:
                    logger.error(f"Scenario '{scenario_name}' not found.")
                    raise ValueError(f"Scenario '{scenario_name}' not found.")

                federation_name = scenario_doc["federation"]
                federation_doc = mgr.read_federation(federation_name)
                if not federation_doc:
                    logger.error(f"Federation '{federation_name}' not found.")
                    raise ValueError(f"Federation '{federation_name}' not found.")
        except Exception as e:
            logger.error(f"Failed to connect or read from metadata backend: {e}")
            raise

        self.federate = federation_doc["federation"][self.federate_name]
        self.config = self.federate["HELICS_config"]
        start_time = scenario_doc["start_time"]
        stop_time = scenario_doc["stop_time"]
        self.model_path = self.federate.get("model_path", "system.glm")
        
        logger.info(f"Preparing GridLAB-D model file: '{self.model_path}'")
        model_path = Path(self.model_path)
        glm = Gridlabd(model_path)
        glm.remove_quotes_from_obj_names()  # clean object names
        glm.remove_outputs()
        glm.clock["starttime"] = "'" + str(start_time).replace("T", " ") + "'"
        glm.clock["stoptime"] =  "'" + str(stop_time).replace("T", " ") + "'"
        self.glm = glm

    def run(self, scenario_name: str):
        """
        Prepares and runs the GridLAB-D co-simulation.

        This is the main entry point which orchestrates the creation and
        execution of the GridLAB-D federate process.
        
        Args:
            scenario_name (str): The name of the scenario to run.
        """
        logger.info(f"Starting setup for GridLAB-D federate '{self.federate_name}'...")
        self.create_federate(scenario_name)
        
        logger.info("Handing off control to GridLAB-D process...")
        # The glmpy library handles launching the GridLAB-D process with the
        # provided HELICS configuration.
        self.glm.run(helics_config=self.config)
        logger.info(f"GridLAB-D federate '{self.federate_name}' finished simulation.")


if __name__ == '__main__':
    # This example shows how to use the class with different backends.
    # It assumes the necessary configuration files/database entries exist.

    # --- Example for a JSON file backend ---
    # This is the default and simplest case.
    
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.DEBUG)
    logger.info("--- Running with JSON backend ---")
    gld_json = FederateGridlabD(fed_name="gld", backend="json", location="./config")
    gld_json.run(scenario_name="gld1")


    # --- Example for a MongoDB backend (commented out by default) ---
    #
    # logger.info("\n--- Running with MongoDB backend ---")
    # gld_mongo = FederateGridlabD(
    #     fed_name="gld_from_mongo",
    #     backend="mongo",
    #     location="localhost",  # or "mongodb://localhost:27017"
    #     database="copper",
    #     user="worker",
    #     password="worker" 
    # )
    # try:
    #     gld_mongo.run(scenario_name="gld_mongo_scenario")
    # except Exception as e:
    #     logger.error(f"Failed to run with MongoDB backend: {e}")
