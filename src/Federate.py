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

import metadataDB as mDB

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
    """

    def __init__(self, fed_name="", **kwargs):
        self.config = None
        self.scenario = None
        self.scenario_name = None
        self.federation = None
        self.federation_name = None
        self.federate = None
        self.federate_type = None
        self.federate_name = fed_name
        self.hfed = None
        self.mddb = None
        self.start = None
        self.stop = None
        self.time_step = -1
        self.stop_time = -1
        self.next_requested_time = -1
        self.granted_time = -1
        self.data_from_federation = {}
        self.data_to_federation = {}
        self.inputs = {}
        self.pubs = {}
        self.endpoints = {}
        self.debug = True
        self.errors = []

        # Initialize the structure of the interface dictionaries
        self.data_from_federation["inputs"] = {}
        self.data_from_federation["endpoints"] = {}
        self.data_to_federation["publications"] = {}
        self.data_to_federation["endpoints"] = {}

        # if not wanting to debug, add debug=False as an argument
        self.__dict__.update(kwargs)

    def connect_to_metadataDB(self):
        """
        The metadata database (metadataDB) contains the HELICS configuration
        JSON along with other pieces of useful configuration or federation
        management data. This method connects to that database and makes it 
        available for other methods in this class.
        """
        try:
            self.mddb = mDB.MetaDB(mDB.cu_uri, mDB.cu_database)
        except Exception as e:
            self.errors.append(str(e))
            return

    def connect_to_helics_config(self):
        self.federate = self.federation[self.federate_name]
        self.federate_type = self.federate["federate_type"]
        # self.time_step = self.federate["time_step"]
        self.time_step = self.federate["HELICS_config"]["period"]
        self.config = self.federate["HELICS_config"]
        # self.image = self.federate["image"]

    def create_federate(self, scenario_name):
        """
        Creates and defines both the instance of this class,
        and the HELICS federate object (self.hfed).
        Any initialization that cannot take place on instantiation of
        the federate object should be done here. In this case, 
        initializing any class attribute values that come from the 
        metadata database have to take place after connecting to
        said database.
        """

        self.connect_to_metadataDB()
        if scenario_name is None:
            raise NameError("scenario_name is None")
        self.scenario_name = scenario_name
        self.scenario = self.mddb.get_dict(mDB.cu_scenarios, None, self.scenario_name)
        self.federation_name = self.scenario["federation"]
        self.start = self.scenario["start_time"]
        self.stop = self.scenario["stop_time"]

        self.federation = self.mddb.get_dict(mDB.cu_federations, None, self.federation_name)
        self.federation = self.federation["federation"]
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

        # setting max in seconds
        ep = datetime.datetime(1970, 1, 1)
        # %:z in version  python 3.12, for now, no time offsets -
        s = datetime.datetime.strptime(self.start, '%Y-%m-%dT%H:%M:%S')
        e = datetime.datetime.strptime(self.stop, '%Y-%m-%dT%H:%M:%S')
        sIdx = (s - ep).total_seconds()
        eIdx = (e - ep).total_seconds()
        self.stop_time = int((eIdx - sIdx))

        self.create_helics_fed()

    def create_helics_fed(self):
        """
        Using the HELICS configuration document from the metadataDB, this
        method creates the HELICS federate. It also populates class 
        attributes that define the inputs, pubs, and endpoints

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

    def run_cosim_loop(self):
        """
        This is a generic HELICS co-sim loop based on a pre-defined maximum
        simulation time. 
        """
        try:
            if self.hfed is None:
                raise Exception(self.errors)
            self.granted_time = 0
            self.enter_initialization()
            self.enter_executing_mode()
            while self.granted_time < self.stop_time:
                self.simulate_next_step()
        except h.HelicsException as e:
            self.errors.append(f"HelicsException at time {self.granted_time}: {e}")
            return
        except Exception as e:
            self.errors.append(f"Exception: {e}")
            return

    def enter_initialization(self):
        """
        There are a few different ways of handling HELICS initializing mode and
        what is implemented here is the simplest. If you need something more
        complex, subclass and overload.
        """
        self.hfed.enter_initializing_mode()

    def enter_executing_mode(self):
        """
        There are a few different ways of handling HELICS executing mode and
        what is implemented here is the simplest. If you need something more
        complex, subclass and overload.
        """
        self.hfed.enter_executing_mode()

    def simulate_next_step(self):
        """
        This method is the core of the main co-simulation loop where the time 
        request is made and once granted, data from the rest of the federation
        is collected and used to update the internal model before
        sending out new data for the rest of the federation to use.
        """
        next_requested_time = self.calculate_next_requested_time()
        self.request_time(next_requested_time)
        self.get_data_from_federation()
        self.update_internal_model()
        self.send_data_to_federation()

    def calculate_next_requested_time(self):
        """
        Many federates run at very regular time steps and thus the calculation
        of the requested time is trivial. In some cases, though, the requested
        time may be more dynamic and this method provides a place for users
        to overload the default calculation method if they need something 
        more complex.
        """
        self.next_requested_time = self.granted_time + self.time_step
        return self.next_requested_time

    def request_time(self, requested_time: float):
        """
        HELICS provides a variety of means of requesting time. The most common
        is a simple hfed.request_time(float) which is a blocking call. There
        are others that make the time request but allow users to continue
        working on something else while they wait for HELICS to get back to
        them with the granted time. This method is here just to allow users
        to subclass and overload the Federate class and re-implement how
        they want to do time-requests.
        """
        self.granted_time = self.hfed.request_time(requested_time)
        pass

    def get_data_from_federation(self):
        """
        This method is an automated way of getting data the rest of the 
        federation has sent out. 

        Directly accessing the value and message interfaces via the HELICS
        federate (hfed object) provides a much richer set of metadata 
        associate with these interfaces.
        """
        # Subscriptions and inputs
        for idx in range(0, self.hfed.n_inputs):
            put = self.hfed.get_subscription_by_index(idx)
            if put.name[0:7] == "_input_":
                key = put.target
                # The name is auto-generated by HELICS and is a subscription
                # logger.debug(f" {self.federate_name} received {put.value} from {put.name}")
            else:
                key = put.name
                # logger.debug(f" {self.federate_name} received {put.value} from {put.name}")

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

        # Endpoints
        for idx in range(0, self.hfed.n_endpoints):
            ep = self.hfed.get_endpoint_by_index
            # Delete out old message list to avoid confusion about when the message came in
            self.data_from_federation[ep.name] = []
            for message in range(0, ep.n_pending_messages):
                self.data_from_federation["endpoints"][ep.name].append(ep.get_message())

    def update_internal_model(self):
        """
        This is entirely user-defined code and is intended to be defined by
        sub-classing and overloading.
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

    def send_data_to_federation(self):
        """
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
        own entry in the pub_data 
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

    def destroy_federate(self):
        """
        As part of ending a HELICS co-simulation it is good housekeeping to
        formally destroy the model federate. Doing so informs the rest of the
        federation that it is no longer a part of the co-simulation and they
        should proceed without it (if applicable). Generally this is done
        when the co-simulation is complete and all federates end execution
        at more or less the same wall-clock time.

        """
        try:
            logger.debug(f'{h.helicsFederateGetName(self.hfed)} being destroyed, max time = {h.HELICS_TIME_MAXTIME}')
            requested_time = int(h.HELICS_TIME_MAXTIME)
            h.helicsFederateClearMessages(self.hfed)
            granted_time = h.helicsFederateRequestTime(self.hfed, requested_time)
            logger.info(f'{h.helicsFederateGetName(self.hfed)} granted time {granted_time}')
            h.helicsFederateDisconnect(self.hfed)
            h.helicsFederateFree(self.hfed)
            # h.helicsCloseLibrary()
            logger.debug(f'Federate {h.helicsFederateGetName(self.hfed)} finalized')
        except Exception as e:
            self.errors.append(str(e))


if __name__ == "__main__":
    test_fed = Federate("Battery")
    test_fed.create_federate("TE30")
    test_fed.run_cosim_loop()
    test_fed.destroy_federate()
    if len(test_fed.errors) > 0:
        logger.warning("Federate failed to execute due to the following errors:")
        for error in test_fed.errors:
            logger.warning(error)
