"""
Created on 12/14/2023

Federate class that defines the basic operations of Python-based federates in
Copper.

@author: Trevor Hardy
trevor.hardy@pnnl.gov
"""
import datetime
import json
import logging

import helics as h

import cosim_toolbox.metadataDB as mDB

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.ERROR)


class Federate:
    """
    This class definition is intended to be a reasonable, generic
    class for Python-based federates in HELICS. It outlines the typical
    federate operational procedure in the "_main_" function; users that
    don't need anything fancy will probably be able to call those few functions
    and get a working federate.

    This class gets its configuration from the metadata database following
    the standard Copper definition of the "federations" document.

    To be overly clear, this class is intended to be sub-classed and overloaded
    to allow users to customize it as necessary. If nothing else, the
    "update_model" method will always need updating to perform the particular
    calculations federate is responsible for. There are several other
    methods that are likely candidates for subclassing based on the
    particular needs of the federate or the larger federation:
    "enter_initializing_mode"
    "enter_executing_mode"
    "time_request"

    All of these have the simplest version of these HELICS operations but there
    are more complex versions that HELICS supports that allow for things like
    iterations and asynchronous or non-blocking operations (further details
    can be found in the HELICS documentation).

    The existing methods to pull in values from the HELICS federation and
    push values out are likely to be sufficient for most federates but, again
    these can be overloaded in a subclass if, for example, the number of
    HELICS inputs and publications is very large and only a few are used during
    a given time-step.

    Attributes:
        hfed: The HELICS federate object used to access the HELICS interfaces
        federate_name (str): The federate name
        federate (dict): Dictionary with all configuration information,
         including but not limited to the HELICS JSON config string
        federate_type (str): The federate type. Must be "value", "message", or "combo"
        config: Valid HELICS config JSON string
        granted_time: The last time granted to this federate
        time_step: The size of the simulated time step takes when requesting the next time
        scenario_name (str): The scenario name
        scenario (dict): Dictionary with all scenario configuration information
        federation_name (str): The federation name
        federation (dict): Dictionary with all federate configuration information
    """

    def __init__(self, fed_name="", **kwargs):
        self.hfed: h.HelicsFederate = None
        self.mddb: mDB.MetaDB = None
        self.config: dict = None
        self.scenario: dict = None
        self.scenario_name: str = None
        self.federation: dict = None
        self.federation_name: str = None
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

        # Initialize the structure of the interface dictionaries
        self.data_from_federation = {"inputs": {}, "endpoints": {}}
        self.data_to_federation = {"publications": {}, "endpoints": {}}

        # if not wanting to debug, add debug=False as an argument
        self.__dict__.update(kwargs)

    def connect_to_metadataDB(self, uri: str, db_name: str) -> None:
        """Connects to the Copper metadataDB

        The metadata database (metadataDB) contains the HELICS configuration
        JSON along with other pieces of useful configuration or federation
        management data. This method connects to that database and makes it
        available for other methods in this class.

        Args:
            uri (str): URI for Mongo database
            db_name (str): Name for Mongo database
        """
        self.mddb = mDB.MetaDB(uri, db_name)
        self.scenario = self.mddb.get_dict(mDB.cu_scenarios, None, self.scenario_name)
        self.federation_name = self.scenario["federation"]
        self.start = self.scenario["start_time"]
        self.stop = self.scenario["stop_time"]

        self.federation = self.mddb.get_dict(mDB.cu_federations, None, self.federation_name)
        self.federation = self.federation["federation"]

        # setting max in seconds
        ep = datetime.datetime(1970, 1, 1)
        # %:z in version  python 3.12, for now, no time offsets (zones)
        s = datetime.datetime.strptime(self.start, '%Y-%m-%dT%H:%M:%S')
        e = datetime.datetime.strptime(self.stop, '%Y-%m-%dT%H:%M:%S')
        s_idx = (s - ep).total_seconds()
        e_idx = (e - ep).total_seconds()
        self.stop_time = int((e_idx - s_idx))

    def connect_to_helics_config(self) -> None:
        """Sets instance attributes to enable HELICS config query of metadataDB

        HELICS configuration information is generally stored in the metadataDB
        and is copied into the `self.federation` attribute. This method pulls
        out a few keys configuration parameters from that attribute to make
        them more easily accessible.
        """
        self.federate = self.federation[self.federate_name]
        self.federate_type = self.federate["federate_type"]
        # self.time_step = self.federate["time_step"]
        self.time_step = self.federate["HELICS_config"]["period"]
        self.config = self.federate["HELICS_config"]
        # self.image = self.federate["image"]

    def create_federate(self, scenario_name: str) -> None:
        """Create Copper and HELICS federates

        Creates and defines both the instance of this class,(the CoSimulation
        federate) and the HELICS federate object (self.hfed). Any
        initialization that cannot take place on instantiation of the
        federate object should be done here. In this case, initializing any
        class attribute values that come from the metadata database have to
        take place after connecting to said database.

        Args:
            scenario_name (str): Name of scenario used to store configuration
                information in the metadataDB

        Raises:
            NameError: Scenario name is undefined (`None`)
        """
        if scenario_name is None:
            raise NameError("scenario_name is None")
        self.scenario_name = scenario_name
        self.connect_to_metadataDB(mDB.cosim_mongo_host, mDB.cosim_mongo_db)
        self.connect_to_helics_config()

        # Provide internal copies of the HELICS interfaces for convenience during debugging.
        if "publications" in self.config.keys():
            for pub in self.config["publications"]:
                self.pubs[pub["key"]] = pub
                self.data_to_federation["publications"][pub['key']] = None
        if "subscriptions" in self.config.keys():
            for sub in self.config["subscriptions"]:
                self.inputs[sub["key"]] = sub
                self.data_from_federation["inputs"][sub['key']] = None
        if "inputs" in self.config.keys():
            for put in self.config["inputs"]:
                self.inputs[put["name"]] = put
                self.data_from_federation["inputs"][put['key']] = None
        if "endpoints" in self.config.keys():
            for ep in self.config["endpoints"]:
                self.endpoints[ep["name"]] = ep
                if 'key' in self.config['endpoints'][ep]:
                    self.data_to_federation['endpoints'][ep['key']] = None
                if 'destination' in self.config['endpoints'][ep]:
                    self.data_from_federation['endpoints'][ep['key']] = None

        self.create_helics_fed()

    def create_helics_fed(self) -> None:
        """Creates the HELICS federate object

        Using the HELICS configuration document from the metadataDB, this
        method creates the HELICS federate. HELICS has distinct APIs for the
        creation of a federate based on its type and thus, the type of federate
        needs to be defined as an instance attribute to enable the correct API
        to be called.

        Raises:
            ValueError: Invalid value for self.federate_type
        """
        if self.federate_type == "value":
            self.hfed = h.helicsCreateValueFederateFromConfig(json.dumps(self.config))
        elif self.federate_type == "message":
            self.hfed = h.helicsCreateMessageFederateFromConfig(json.dumps(self.config))
        elif self.federate_type == "combo":
            self.hfed = h.helicsCreateCombinationFederateFromConfig(json.dumps(self.config))
        else:
            raise ValueError(f"Federate type \'{self.federate_type}\'"
                             f" not allowed; must be 'value', 'message', or 'combo'.")

    def run_cosim_loop(self) -> None:
        """Runs the generic HELICS co-sim loop

        This HELICS co-sim loop runs until it the simulated time reaches
        self.stop_time. self.enter_initialization_mode() and
        self.enter_executing_mode(), and self. simulate_next_step
        have been implemented and should be overloaded/redefined as necessary
        to fit the needs of a given federate and/or federation.
        """
        if self.hfed is None:
            raise ValueError("Helics Federate object has not been created")
        self.granted_time = 0
        self.enter_initialization()
        self.enter_executing_mode()
        while self.granted_time < self.stop_time:
            self.simulate_next_step()

    def enter_initialization(self) -> None:
        """Moves federate to HELICS initializing mode

        There are a few stages to a federate in HELICS with initializing mode
        being the first after the Federate is created. Entering initializing
        mode is a global synchronous event for all federates and provides an
        opportunity to do some fancy things around dynamic configuration of the
        Federate. What is implemented here is the simplest, most vanilla means
        of entering initializing mode. If you need something more complex,
        overload or redefine this method.
        """
        self.hfed.enter_initializing_mode()

    def enter_executing_mode(self) -> None:
        """Moves the Federate to executing mode

        Similar to initializing mode, there are a few different ways of
        handling HELICS executing mode and what is implemented here is the
        simplest. If you need something more complex or specific, overload
        or redefine this method.
        """
        self.hfed.enter_executing_mode()

    def simulate_next_step(self) -> None:
        """Advances the Federate to its next simulated time

        This method is the core of the main co-simulation loop where the time
        request is made and once granted, data from the rest of the federation
        is collected and used to update the internal model before sending out
        new data for the rest of the federation to use.
        """
        next_requested_time = self.calculate_next_requested_time()
        self.request_time(next_requested_time)
        self.get_data_from_federation()
        self.update_internal_model()
        self.send_data_to_federation()

    def calculate_next_requested_time(self) -> float:
        """Determines the next simulated time to request from HELICS

        Many federates run at very regular time steps and thus the calculation
        of the requested time is trivial. In some cases, though, the requested
        time may be more dynamic and this method provides a place for users
        to overload the default calculation method if they need something more complex.

        Returns:
            self.next_requested_time: Calculated time for the next HELICS time request
        """
        self.next_requested_time = self.granted_time + self.time_step
        return self.next_requested_time

    def request_time(self, requested_time: float) -> float:
        """Requests next simulated time from HELICS

        HELICS provides a variety of means of requesting time. The most common
        is a simple hfed.request_time(float) which is a blocking call. There
        are others that make the time request but allow users to continue
        working on something else while they wait for HELICS to get back to
        them with the granted time. This method is here just to allow users
        to redefine or overload and re-implement how they want to do time requests.

        Args:
            requested_time: Simulated time this federate needs to request

        Returns:
            self.granted_time: Simulated time granted by HELICS
        """
        self.granted_time = self.hfed.request_time(requested_time)
        return self.granted_time

    def get_data_from_federation(self) -> None:
        """Collects inputs from federation and stores them

        This method is an automated way of getting data the rest of the
        federation has sent out. Directly accessing the value and message
        interfaces via the HELICS federate (hfed object) provides a much richer
        set of metadata associated with these interfaces. The implementation
        here is vanilla and is expected to be sufficient for many use cases.
        """
        # Subscriptions and inputs
        for idx in range(0, self.hfed.n_inputs):
            put = self.hfed.get_subscription_by_index(idx)
            if put.name[0:7] == "_input_":
                key = put.target
                # The name is auto-generated by HELICS and is a subscription
                logger.debug(f"Auto input idx {idx} key {key} put {put}")
            else:
                key = put.name
                logger.debug(f"Input idx {idx} key {key} put {put}")

            d_type = self.inputs[key]['type'].lower()
            if d_type == "double":
                self.data_from_federation["inputs"][key] = put.double
            elif d_type == "integer":
                self.data_from_federation["inputs"][key] = put.integer
            elif d_type == "complex":
                self.data_from_federation["inputs"][key] = put.complex
            elif d_type == "string":
                self.data_from_federation["inputs"][key] = put.string
            elif d_type == "vector":
                self.data_from_federation["inputs"][key] = put.vector
            elif d_type == "complex vector":
                self.data_from_federation["inputs"][key] = put.complex_vector
            elif d_type == "boolean":
                self.data_from_federation["inputs"][key] = put.boolean
            else:
                logger.debug(f"Key {key} unknown type -> {d_type} object {put}")

        # Endpoints
        for idx in range(0, self.hfed.n_endpoints):
            ep = self.hfed.get_endpoint_by_index
            # Delete out old message list to avoid confusion about when the message came in
            self.data_from_federation[ep.name] = []
            for message in range(0, ep.n_pending_messages):
                if ep.name not in self.data_to_federation["endpoints"]:
                    self.data_from_federation["endpoints"][ep.name] = []
                self.data_from_federation["endpoints"][ep.name].append(ep.get_message().data)

    def update_internal_model(self) -> None:
        """Perform federate specific calculations to bring model up to date

        After receiving inputs from the rest of the federation, each federate
        updates its internal model, generally using the new inputs to perform
        the necessary calculations. This aligns the Federate state with that
        of the rest of the federation

        This is entirely user-defined code and is intended to be defined by
        sub-classing and/or overloading.
        """
        if not self.debug:
            raise NotImplementedError("Subclass from Federate and write code to update internal model")
        # Doing something silly for testing purposes
        # Get a value from an arbitrary input; I hope it is a number
        if len(self.data_from_federation["inputs"].keys()) >= 1:
            key = list(self.data_from_federation["inputs"].keys())[0]
            dummy_value = self.data_from_federation["inputs"][key]
        else:
            dummy_value = 0

        # Increment for arbitrary reasons. This is the actual model
        # that is being updated in this example.
        dummy_value += 1
        print(dummy_value)

        # Send out incremented value on arbitrary publication
        # Clear out values published last time
        for pub in self.data_to_federation["publications"]:
            self.data_to_federation["publications"][pub] = None
        for ep in self.data_to_federation["endpoints"]:
            self.data_to_federation["endpoints"][ep] = None

        if len(self.data_to_federation["publications"].keys()) >= 1:
            pub = self.hfed.get_publication_by_index(0)
            self.data_to_federation["publications"][pub.name] = dummy_value

    def send_data_to_federation(self) -> None:
        """Sends specified outputs to rest of HELICS federation

        This method provides an easy way for users to send out any data
        to the rest of the federation. Users pass in a dict structured the same
        as the "data_from_federation" with sub-dicts for publications and
        endpoints and keys inside those dicts for the name of the pub or
        endpoint. The value for the keys is slightly different, though:
            - pubs: value is the data to send
            - endpoints: value is a dictionary as follows
                {
                    "destination": <target endpoint name, may be an empty string>
                    "payload": <data to send>
                }

        Since endpoints can send multiple messages, each message needs its
        own entry in the pub_data.
        """

        # Publications
        for key, value in self.data_to_federation["publications"].items():
            pub = self.hfed.get_publication_by_name(key)
            pub.publish(value)
            logger.debug(f" {self.federate_name} publication {key}, {value}")

        # Endpoints
        for key, value in self.data_to_federation["endpoints"].items():
            ep = self.hfed.get_endpoint_by_name(key)
            if value["destination"] == "":
                ep.send_data(value["payload"])
            else:
                ep.send_data(value["payload"], value["destination"])

    def destroy_federate(self) -> None:
        """Removes HELICS federate from federation

        As part of ending a HELICS co-simulation it is good housekeeping to
        formally destroy the model federate. Doing so informs the rest of the
        federation that it is no longer a part of the co-simulation and they
        should proceed without it (if applicable). Generally this is done
        when the co-simulation is complete and all federates end execution
        at more or less the same wall-clock time.
        """

        logger.debug(f'{h.helicsFederateGetName(self.hfed)} being destroyed, '
                     f'max time = {h.HELICS_TIME_MAXTIME}')
        requested_time = int(h.HELICS_TIME_MAXTIME)
        h.helicsFederateClearMessages(self.hfed)
        granted_time = h.helicsFederateRequestTime(self.hfed, requested_time)
        logger.info(f'{h.helicsFederateGetName(self.hfed)} granted time {granted_time}')
        h.helicsFederateDisconnect(self.hfed)
        h.helicsFederateFree(self.hfed)
        h.helicsFederateFree(self.hfed)
        # h.helicsCloseLibrary()
        logger.debug(f'Federate {h.helicsFederateGetName(self.hfed)} finalized')


if __name__ == "__main__":
    test_fed = Federate("Battery")
    test_fed.create_federate("TE30")
    test_fed.run_cosim_loop()
    test_fed.destroy_federate()
