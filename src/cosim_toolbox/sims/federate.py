"""
Created on 12/14/2023

Federate class that defines the basic operations of Python-based federates in
CoSim Toolbox (CST).

@author: Trevor Hardy
trevor.hardy@pnnl.gov
"""

import datetime
import json
import logging
from typing import Any, Dict, Optional

import helics as h

from cosim_toolbox.dbms import MetadataManager, TimeSeriesManager, TSRecord
from cosim_toolbox.dbms import create_metadata_manager, create_timeseries_manager

logger = logging.getLogger(__name__)


class Federate:
    """
    This class definition is intended to be a reasonable, generic
    class for Python-based federates in HELICS. It outlines the typical
    federate operational procedure in the "_main_" function; users that
    don't need anything fancy will probably be able to call those few
    functions and get a working federate.

    This class gets its configuration from the metadata database following
    the standard CST definition of the "federations" document.

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
        config (dict): Valid HELICS config JSON string
        granted_time (float): The last time granted to this federate
        period (float): The size of the simulated time step takes when requesting the next time
        scenario_name (str): The scenario name
        scenario (dict): Dictionary with all scenario configuration information
        federation_name (str): The federation name
        federation (dict): Dictionary with all federate configuration information
    """

    def __init__(
            self,
            fed_name: str = "",
            *,
            debug: bool = True,
    ):
        """Initializes the Federate.

        Args:
            fed_name (str, optional): The name of the Federate. Defaults to "".
            debug (bool, optional): A flag for enabling debug behaviors. Defaults to True.
        """
        # HELICS and Manager Objects
        self.hfed: Optional[h.HelicsFederate] = None
        self.metadata_manager: Optional[MetadataManager] = None
        self.timeseries_manager: Optional[TimeSeriesManager] = None

        # Configuration Attributes (initialized later)
        self.config: Optional[Dict[str, Any]] = None
        self.scenario: Optional[Dict[str, Any]] = None
        self.scenario_name: Optional[str] = None
        self.federation: Optional[Dict[str, Any]] = None
        self.federation_name: Optional[str] = None
        self.federate: Optional[Dict[str, Any]] = None
        self.federate_type: Optional[str] = None
        self.federate_name: Optional[str] = fed_name
        self.analysis_name: Optional[str] = None

        # Time and Control Attributes
        self.start: Optional[str] = None
        self.stop: Optional[str] = None
        self.no_t_start = None
        self.period = -1.0
        self.stop_time = -1.0
        self.granted_time = -1.0
        self.next_requested_time = -1.0
        self.debug = True

        # Internal State Attributes
        self._use_timescale: bool = False
        self._s: Optional[datetime.datetime] = None
        self._ep: Optional[datetime.datetime] = None
        self._count = 0
        self.interval = 1000

        # Data Interface Dictionaries
        self.fed_collect = "maybe"
        self.pubs: Dict[str, Any] = {}
        self.inputs: Dict[str, Any] = {}
        self.endpoints: Dict[str, Any] = {}
        self.data_from_federation: Dict[str, Dict] = {"inputs": {}, "endpoints": {}}
        self.data_to_federation: Dict[str, Dict] = {"publications": {}, "endpoints": {}}

    @property
    def use_timescale(self) -> bool:
        """Sets the timescale flag

        Returns:
            bool: state of timescale flag
        """
        return self._use_timescale

    @use_timescale.setter
    def use_timescale(self, value: bool):
        """Sets timescale based on passed-in value

        Args:
            value (bool): Value of timescale flag

        Returns:
            None
        """
        self._use_timescale = value

    def set_metadata(self) -> None:
        """Sets instance attributes to enable HELICS config query of metadata
        data store.

        HELICS configuration information is generally stored in the metadataDB
        and is copied into the `self.federation` attribute. This method pulls
        out a few keys configuration parameters from that attribute to make
        them more easily accessible.

        Return:
            None
        """

        # setting start and stop time
        self.start = self.scenario["start_time"]
        self.stop = self.scenario["stop_time"]
        # setting max in seconds
        ep = datetime.datetime(1970, 1, 1)
        # %:z in version  python 3.12, for now, no time offsets (zones)
        s = datetime.datetime.strptime(self.start, "%Y-%m-%dT%H:%M:%S")
        e = datetime.datetime.strptime(self.stop, "%Y-%m-%dT%H:%M:%S")
        s_idx = (s - ep).total_seconds()
        e_idx = (e - ep).total_seconds()
        self.stop_time = int((e_idx - s_idx))
        self.no_t_start = self.start.replace('T', ' ')
        self._s = datetime.datetime.strptime(self.start, "%Y-%m-%dT%H:%M:%S")

    def get_helics_config(self) -> None:
        """Sets instance attributes to enable HELICS config query of dbConfigs

        HELICS configuration information is generally stored in the dbConfigs
        and is copied into the `self.federation` attribute. This method pulls
        out a few keys configuration parameters from that attribute to make
        them more easily accessible.

        Returns:
            None
        """
        self.federate = self.federation[self.federate_name]
        self.federate_type = self.federate["federate_type"]
        self.period = self.federate["HELICS_config"]["period"]
        self.config = self.federate["HELICS_config"]
        # setting up data logging
        if self.config.get("tags"):
            self.fed_collect = self.config["tags"].get("logger", self.fed_collect)

    def create_federate(self, scenario_name: str,
                        use_meta_db: str ="mongo",
                        use_data_db: str ="postgres") -> None:
        """Create CST and HELICS federates

        Creates and defines both the instance of this class,(the Co-Simulation
        federate) and the HELICS federate object (self.hfed). Any
        initialization that cannot take place on instantiation of the
        federate object should be done here. In this case, initializing any
        class attribute values that come from the metadata database have to
        take place after connecting to said database.

        Args:
            scenario_name (str): Name of scenario used to store configuration information in the dbConfigs
            use_meta_db (str, optional): Whether to use a metadata database (e.g., MongoDB). Defaults to mongo.
            use_data_db (str, optional): Whether to use a timeseries database (e.g., PostgresSQL). Defaults to postgres.

        Raises:
            NameError: Scenario name is undefined (`None`)

        Returns:
            None
        """
        if scenario_name is None:
            raise NameError("scenario_name is None")
        self.scenario_name = scenario_name

        self.metadata_manager = create_metadata_manager(use_meta_db)
        self.metadata_manager.connect()
        self.scenario = self.metadata_manager.read_scenario(self.scenario_name)
        if not self.scenario:
            raise ValueError(f"Scenario '{self.scenario_name}' not found in metadata store.")
        self.analysis_name = self.scenario.get("analysis")
        if not self.analysis_name:
            raise ValueError(f"Scenario '{self.scenario_name}' does not specify a 'analysis'.")
        self.federation_name = self.scenario.get("federation")
        if not self.federation_name:
            raise ValueError(f"Scenario '{self.scenario_name}' does not specify a 'federation'.")
        self.federation = self.metadata_manager.read_federation(self.federation_name)['federation']
        if not self.federation:
            raise ValueError(f"Federation '{self.federation_name}' not found in metadata store.")

        self.set_metadata()
        self.get_helics_config()

        # Provide internal copies of the HELICS interfaces for convenience during debugging.
        if "publications" in self.config.keys():
            for pub in self.config["publications"]:
                name = pub.get("name", pub.get("key"))
                self.pubs[name] = pub
                self.data_to_federation["publications"][name] = None
        if "subscriptions" in self.config.keys():
            for sub in self.config["subscriptions"]:
                target = sub.get("target", sub.get("key"))
                self.inputs[target] = sub
                self.data_from_federation["inputs"][target] = None
        if "inputs" in self.config.keys():
            for put in self.config["inputs"]:
                self.inputs[put["name"]] = put
                self.data_from_federation["inputs"][put["key"]] = None
        if "endpoints" in self.config.keys():
            for ep in self.config["endpoints"]:
                self.endpoints[ep["name"]] = ep
                self.data_to_federation["endpoints"][ep["name"]] = None
                if "destination" in ep:
                    self.data_from_federation["endpoints"][ep["destination"]] = None
                else:
                    self.data_from_federation["endpoints"][ep["name"]] = None

        self.timeseries_manager = create_timeseries_manager(use_data_db, self.analysis_name)
        # Connect to the timeseries backend
        self.timeseries_manager.connect()

        self.create_helics_fed()
        logger.info(f"Created federate for {self.hfed.name}")

    def create_helics_fed(self) -> None:
        """Creates the HELICS federate object

        Using the HELICS configuration document from the dbConfigs, this
        method creates the HELICS federate. HELICS has distinct APIs for the
        creation of a federate based on its type and thus, the type of federate
        needs to be defined as an instance attribute to enable the correct API
        to be called.

        Raises:
            ValueError: Invalid value for self.federate_type

        Returns:
            None
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

    def on_start(self) -> None:
        """Functionality executed prior to entering initializing

        By default, no functionality is implemented

        Returns:
            None
        """
        pass

    def on_enter_initialization_mode(self) -> None:
        """Functionality executed after entering initialization

        By default, no functionality is implemented

        Returns:
            None
        """
        pass

    def on_enter_executing_mode(self) -> None:
        """Functionality executed after entering executing mode

        By default, no functionality is implemented

        Returns:
            None
        """
        pass

    def run_cosim_loop(self) -> None:
        """Runs the generic HELICS co-sim loop

        This HELICS co-sim loop runs until it the simulated time reaches
        self.stop_time. self.enter_initialization_mode() and
        self.enter_executing_mode(), and self. simulate_next_step
        have been implemented and should be overloaded/redefined as necessary
        to fit the needs of a given federate and/or federation.

        Returns:
            None
        """
        if self.hfed is None:
            raise ValueError("Helics Federate object has not been created")
        self.granted_time = 0
        self.on_start()
        self.enter_initialization()
        self.on_enter_initialization_mode()
        self.enter_executing_mode()
        self.on_enter_executing_mode()
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

        Returns:
            None
        """
        self.hfed.enter_initializing_mode()

    def enter_executing_mode(self) -> None:
        """Moves the Federate to executing mode

        Similar to initializing mode, there are a few different ways of
        handling HELICS executing mode and what is implemented here is the
        simplest. If you need something more complex or specific, overload
        or redefine this method.

        Returns:
            None
        """
        self.hfed.enter_executing_mode()

    def simulate_next_step(self) -> None:
        """Advances the Federate to its next simulated time

        This method is the core of the main co-simulation loop where the time
        request is made and once granted, data from the rest of the federation
        is collected and used to update the internal model before sending out
        new data for the rest of the federation to use.

        Returns:
            None
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
        to overload the default calculation method if they need something more
        complex.

        Returns:
            self.next_requested_time: Calculated time for the next HELICS time
                request
        """
        self.next_requested_time = self.granted_time + self.period
        return self.next_requested_time

    def request_time(self, requested_time: float) -> float:
        """Requests next simulated time from HELICS

        HELICS provides a variety of means of requesting time. The most common
        is a simple hfed.request_time(float) which is a blocking call. There
        are others that make the time request but allow users to continue
        working on something else while they wait for HELICS to get back to
        them with the granted time. This method is here just to allow users
        to redefine or overload and re-implement how they want to do time
        requests.

        Args:
            requested_time: Simulated time this federate needs to request

        Returns:
            self.granted_time: Simulated time granted by HELICS
        """
        self.granted_time = self.hfed.request_time(requested_time)
        return self.granted_time

    def reset_data_to_federation(self) -> None:
        """Sets all values in dictionary of values being sent out
        via publications and endpoints in the data_to_federation
        dictionary to "None".

        Any values in these dictionaries set to `None` do not result in a new
        output via HELICS. This method wipes out all data so that only entries
        added to the dictionary after calling this method will be published,
        preventing duplicate publication of data that has not changed and does
        not need to be re-sent. This also helps manage the data being logged in
        the time-series database.

        Returns:
            None
        """

        for key in self.data_to_federation["publications"].keys():
            self.data_to_federation["publications"][key] = None

        for key in self.data_to_federation["endpoints"].keys():
            self.data_to_federation["endpoints"][key] = None

    def get_data_from_federation(self) -> None:
        """Collects inputs from federation and stores them

        This method is an automated way of getting data the rest of the
        federation has sent out. Directly accessing the value and message
        interfaces via the HELICS federate (hfed object) provides a much richer
        set of metadata associated with these interfaces. The implementation
        here is vanilla and is expected to be sufficient for many use cases.

        Returns:
            None
        """
        # Subscriptions and inputs

        # Delete out old inputs list to avoid confusion
        for key in self.data_from_federation["inputs"]:
            self.data_from_federation["inputs"][key] = []

        for idx in range(0, self.hfed.n_inputs):
            put = self.hfed.get_subscription_by_index(idx)
            if put.name[0:7] == "_input_":
                key = put.target
                # The name is auto-generated by HELICS and is a subscription
                logger.debug(f"Auto input idx: {idx} key: {key} put: {put}")
            else:
                key = put.name
                logger.debug(f"Input idx: {idx} key: {key} put: {put}")

            d_type = self.inputs[key]["type"].lower()
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
                logger.debug(f"Key: {key} unknown type: {d_type} object: {put}")

        # Endpoints
        # Delete out old message list to avoid confusion
        for name in self.data_from_federation["endpoints"]:
            self.data_from_federation["endpoints"][name] = []

        for idx in range(0, self.hfed.n_endpoints):
            ep = self.hfed.get_endpoint_by_index(idx)
            for message in range(0, ep.n_pending_messages):
                data = ep.get_message()
                if ep.default_destination in self.data_from_federation["endpoints"]:
                    self.data_from_federation["endpoints"][ep.default_destination].append(data)
                else:
                    self.data_from_federation["endpoints"][ep.name].append(data)
                logger.info(f"Message: {idx} endpoint: {ep}, data: {data}")

    def update_internal_model(self) -> None:
        """Perform federate specific calculations to bring model up to date

        After receiving inputs from the rest of the federation, each federate
        updates its internal model, generally using the new inputs to perform
        the necessary calculations. This aligns the Federate state with that
        of the rest of the federation

        This is entirely user-defined code and is intended to be defined by
        sub-classing and/or overloading.

        Returns:
            None
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

    def send_data_to_federation(self, reset=False) -> None:
        """
        Sends specified outputs to rest of HELICS federation

        This method provides an easy way for users to send out any data
        to the rest of the federation. Users pass in a dict structured the same
        as the "data_from_federation" with sub-dicts for publications and
        endpoints and keys inside those dicts for the name of the pub or endpoint.
        The value for the keys is slightly different, though:

            pubs: value is the data to send
            endpoints: value is a dictionary as follows::

                {
                    "destination": <target endpoint name, may be an empty string>
                    "payload": <data to send>
                }

        Since endpoints can send multiple messages, each message needs its
        own entry in the pub_data.

        Args:
            reset (bool, optional): When set erases published value which
                prevents re-publication of the value until manually set to a
                non-`None` value. Any entry in this dictionary that is `None`
                is not sent out via HELICS. Defaults to False.

        Returns:
            None
        """

        # Publications
        for key, value in self.data_to_federation["publications"].items():
            if value is not None:
                pub = self.hfed.get_publication_by_name(key)
                pub.publish(value)
                logger.debug(f" {self.federate_name} publication: {key}, value: {value}")

                # data logger
                _pub = self.pubs[key]
                table = f"hdt_{_pub['type'].lower()}"
                item_collect = _pub.get("tags", {}).get("logger", "maybe")
                if item_collect == "yes" or (item_collect == "maybe" and self.fed_collect != "no"):
                    self.write_to_logger(self.federate_name, key, value, table=table)

                if reset:
                    self.data_to_federation["publications"][key] = None

        # Endpoints
        for key, messages in self.data_to_federation["endpoints"].items():
            if messages is not None:
                ep = self.hfed.get_endpoint_by_name(key)
                for msg in messages:
                    if isinstance(msg, dict) and "payload" in msg:
                        # New documented format: msg is {"payload": ..., "destination": ...}
                        payload = msg["payload"]
                        destination = msg.get("destination", ep.default_destination)
                    else:
                        # Legacy format: msg is the payload itself
                        payload = msg
                        destination = ep.default_destination
                    ep.send_data(payload, destination)
                    receiving_endpoint = destination
                    receiving_federate = receiving_endpoint.split("/")[0] if "/" in receiving_endpoint else ""
                    # data logger
                    _endpts = self.endpoints[key]
                    item_collect = _endpts.get("tags", {}).get("logger", "maybe")
                    # Log if: item is "yes", OR item is "maybe" and federate is not "no".
                    if item_collect == "yes" or (item_collect == "maybe" and self.fed_collect != "no"):
                        self.write_to_logger(self.federate_name, key, payload, table="hdt_endpoint", receiving_federate=receiving_federate, receiving_endpoint=receiving_endpoint)

                logger.debug(
                    f" {self.federate_name} endpoint: {key}, default destination: {ep.default_destination}, messages: {messages}")

                if reset:
                    self.data_to_federation["endpoints"][key] = None

    def write_to_logger(self, name: str, 
                        key: str, 
                        value: Any, 
                        table: str = None, 
                        message_time: float = None, 
                        receiving_federate: str = None, 
                        receiving_endpoint: str = None):
        """Populates a TSRecord object with the output of a publication or 
        endpoint and adds it to the timeseries data manager queue of data to
        write.

        Args:
            name (str): Name of the federate sending the data
            key (str): Name of the key associated with the data (pub or 
            endpoint name)
            value (Any): Value being sent
            table (str, optional): DEPRECATED. Defaults to None.
            message_time (float, optional): Simulation ordinal time when data
              is being sent. Defaults to None.
            receiving_federate (str, optional): Name of federate being sent
              the message (endpoint only). Defaults to None.
            receiving_endpoint (str, optional): Name of endpoint receiving
              the message (endpoint only). Defaults to None.
        """

        # The 'table' argument is no longer needed as the manager handles types.
        if self.timeseries_manager:
            # Construct the real_time timestamp
            # Note: This logic assumes granted_time is in seconds.
            if message_time is None:
                message_time = self.granted_time
            time_delta = datetime.timedelta(seconds=int(message_time))
            real_time = self._s + time_delta

            # Create a TSRecord object
            record = TSRecord(
                real_time=real_time,
                sim_time=float(self.granted_time),
                scenario=self.scenario_name,
                federate=name,
                data_name=key,
                data_value=value,
                receiving_federate=receiving_federate,
                receiving_endpoint=receiving_endpoint,
                data_type=table
            )

            # Add the record to the manager's buffer
            self.timeseries_manager.add_record(record)
            # simple implementation of to commit every self.interval bytes or so
            self._count += 1
            if self._count > self.interval:
                self.timeseries_manager.flush()
                self._count = 0

    def destroy_federate(self) -> None:
        """Removes HELICS federate from federation

        As part of ending a HELICS co-simulation it is good housekeeping to
        formally destroy the model federate. Doing so informs the rest of the
        federation that it is no longer a part of the co-simulation and they
        should proceed without it (if applicable). Generally this is done
        when the co-simulation is complete and all federates end execution
        at more or less the same wall-clock time.
        """

        logger.debug(f"{h.helicsFederateGetName(self.hfed)} being destroyed, "
                     f"max time = {h.HELICS_TIME_MAXTIME}")
        if self.timeseries_manager:
            self.timeseries_manager.flush()
            self.timeseries_manager.disconnect()
        if self.metadata_manager:
            self.metadata_manager.disconnect()
        h.helicsFederateClearMessages(self.hfed)
        # TODO: there is a bug for h.helicsFederateRequestTime
        # requested_time = int(h.helicsFederateRequestTime)
        # granted_time = h.helicsFederateRequestTime(self.hfed, requested_time)
        # logger.info(f'{h.helicsFederateGetName(self.hfed)} granted time {granted_time}')

        h.helicsFederateDisconnect(self.hfed)
        h.helicsFederateFree(self.hfed)
        # h.helicsCloseLibrary()
        logger.debug(f"Federate {h.helicsFederateGetName(self.hfed)} finalized")

    @property
    def current_time(self):
        if self.hfed is not None:
            return self.hfed.current_time
        raise RuntimeError("Federate not yet created. Cannot get current time.")

    def run(self, scenario_name: str,
            use_meta_db: str ="mongo",
            use_data_db: str ="postgres") -> None:
        """Runs the HELICS federate class

        Args:
            scenario_name (str): Name of scenario used to store configuration information in the dbConfigs
            use_meta_db (str, optional): Whether to use a metadata database (e.g., MongoDB). Defaults to mongo.
            use_data_db (str, optional): Whether to use a timeseries database (e.g., PostgresSQL). Defaults to postgres.
        """
        self.create_federate(scenario_name, use_meta_db, use_data_db)
        self.run_cosim_loop()
        self.destroy_federate()
