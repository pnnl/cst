"""
Created on 12/14/2023

Federate class that defines the basic operations of Python-based federates in
Copper.

@author: Trevor Hardy
trevor.hardy@pnnl.gov
"""

import helics as h
import logging
from metadataDB import MetaDB
import json

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.ERROR)

class Federate():
    """
    This federate class definition is intended to be a reasonable, generic 
    class for Python-based federates in HELICS. It outlines the typical 
    federate operational procedure in the "_main_" function; users that
    don't need anything fancy will probably be able to call those few functions
    and get a working federate.

    This class gets its configuration from the metadata database following
    the standard Copper definition of the "federation" document. 

    To be overly clear, this class is intended to be sub-classed and overloaded
    to allow users to customize it as necessary. If nothing else, the 
    "update_model" method will always need updating to perform the particular
    calculations the federate is responsible for. There are several other
    methods that are likely candidates for subclassing based on the 
    particular needs of the federate or the larger federation:
    "enter_initializing_mode"
    "enter_executing_mode"
    "time_request"

    All of these have the simplest version of these HELICS operations but there
    are more complex versions that HELICS supports that allow for things like
    itterations and asynchronous or non-blocking operations (further details
    can be found in the HELICS documentation).

    The existing methods to pull in values from the HELICS federation and
    push values out are likely to be sufficient for most federates but, again
    these can be overloaded in a sub-class if, for example, the number of 
    HELICS inputs and publications is very large and only a few are used during
    a given time-step.
    """

    def __init__(self, fed_name="", **kwargs):
        self.hfed = None
        self.mddb = None
        self.main_collection = "main"
        self.fed_name = fed_name
        self.sim_step_size = -1
        self.max_sim_time = -1
        self.next_requested_time = None
        self.granted_time = None
        self.data_from_federation = {}
        self.data_to_federation = {}
        self.inputs = {}
        self.pubs = {}
        self.endpoints = {}


        # Initialize the structure of the interface dictionaries
        self.data_from_federation["inputs"] = {}
        self.data_from_federation["endpoints"] = {}
        self.data_to_federation["publications"] = {}
        self.data_to_federation["endpoints"] = {}

        # stackoverflow said I could do this and allow users to instantiate
        # this doing something like:
        # fed = Federate(fed_name = "heat_pump12")
        # and this would set self.name = "heatpump12"
        # Seems like a good idea to me; I hope it works.
        self.__dict__.update(kwargs)

    def connect_to_metadataDB(self):
        """
        The metadata database (metadataDB) contains the HELICS configuration
        JSON along with other pieces of useful configuration or federation
        management data. This method connects to that database and makes it 
        available for other methods in this class.
        """
        local_default_uri = 'mongodb://localhost:27017'
        uri = local_default_uri
        self.mddb = MetaDB(uri_string=uri)

    def create_federate(self):
        """
        Creates and defines both the instance of this Federate class as well
        as the HELICS federate object (self.hfed).
        """
        scenario_name = self.create_helics_fed()
        self.initialize_fed(scenario_name)
    
    def initialize_fed(self, scenario_name):
        """
        Any initialization that cannot take place on instantiation of
        the federate object should be done here. In this case, 
        initializing any class attribute values that come from the 
        metadata database have to take place after connecting to
        said database.
        """
        fed_dict = self.mddb.get_dict(scenario_name, dict_name="federation")[self.fed_name]
        helics_dict = fed_dict["HELICS config"]
        self.sim_step_size = fed_dict["sim step size"]
        self.max_sim_time = self.mddb.get_dict(scenario_name, dict_name="federation")["max sim time"]
        if "publications" in helics_dict:
            for pub in helics_dict['publications']:
                self.data_to_federation["publications"][pub['key']] = None
        if "inputs" in helics_dict:
            for inp in helics_dict['inputs']:
                self.data_from_federation["inputs"][inp['key']] = None
        if "subscriptions" in helics_dict:
            for inp in helics_dict['subscriptions']:
                self.data_from_federation["inputs"][inp['key']] = None
        if 'endpoints' in helics_dict:
            for ep in helics_dict['endpoints']:
                if 'key' in helics_dict['endpoints'][ep]:
                    self.data_to_federation['endpoints'][ep['key']] = None
                if 'destination' in helics_dict['endpoints'][ep]:
                    self.data_from_federation['endpoints'][ep['key']] = None

    def create_helics_fed(self):
        """
        Using the HELICS configuration document from the metadataDB, this
        method creates the HELICS federate.

        """
        scenario_name = self.mddb.get_dict(self.main_collection, dict_name="current scenario")["current scenario"]
        fed_def = self.mddb.get_dict(scenario_name, dict_name="federation")[self.fed_name]
        if fed_def["federate type"] == "value":
            self.hfed = h.helicsCreateValueFederateFromConfig(json.dumps(fed_def["HELICS config"]))
        elif fed_def["federate type"] == "message":
            self.hfed = h.helicsCreateMessageFederateFromConfig(json.dumps(fed_def["HELICS config"]))
        elif fed_def["federate type"] == "combo":
            self.hfed = h.helicsCreateCombinationFederateFromConfig(json.dumps(fed_def["HELICS config"]))
        else:
            raise ValueError(f"Federate type \'{fed_def['federate type']}\' not allowed; must be 'value','message', or 'combo'.")
        
        # Provide internal copies of the HELICS interfaces for convenience
        # during debugging.
        if "publications" in fed_def["HELICS config"].keys():
            for pub in fed_def["HELICS config"]["publications"]:
                self.pubs[pub["key"]] = pub
        if "subscriptions" in fed_def["HELICS config"].keys():
            for sub in fed_def["HELICS config"]["subscriptions"]:
                self.inputs[sub["key"]] = sub
        if "inputs" in fed_def["HELICS config"].keys():
            for input in fed_def["HELICS config"]["inputs"]:
                self.inputs[input["name"]] = input
        if "endpoints" in fed_def["HELICS config"].keys():
            for ep in fed_def["HELICS config"]["endpoints"]:
                self.endpoints[ep["name"]] = ep

        return scenario_name

    def run_cosim_loop(self):
        """
        This is a generic HELICS co-sim loop based on a pre-defined maximum
        simulation time. 
        """
        self.granted_time = 0
        self.enter_intialization()
        self.enter_executing_mode()
        while self.granted_time < self.max_sim_time:
            self.simulate_next_step()

    def enter_intialization(self):
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
        is collected and used to update the federate's internal model before
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
        self.next_requested_time = self.granted_time + self.sim_step_size
        return self.next_requested_time

    def request_time(self, requested_time:float):
        """
        HELICS provides a variety of means of requesting time. The most common
        is a simple hfed.request_time(float) which is a blocking call. There
        are others that make the time request but allow users to continue
        working on something else while they wait for HELICS to get back to
        them with the granted time. This method is here just to allow users
        to sub-class and overload the Federate class and re-implement how
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
            input = self.hfed.get_subscription_by_index(idx)
            if input.name[0:7] == "_input_":
                # The name is auto-generated by HELICS and is a subscription
                self.data_from_federation["inputs"][input.target] = input.value
            else:
                self.data_from_federation["inputs"][input.name] = input.value
        
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
        # Doing something silly for testing purposes
        # Get a value from an arbitrary input; I hope its a number
        if len(self.data_from_federation["inputs"].keys()) >= 1:
            key = list(self.data_from_federation["inputs"].keys())[0]
            dummy_value = self.data_from_federation["inputs"][key]
        else:
            dummy_value = 0
        
        # Increment for arbitrary reasons. This is the actual model
        # that is being updated in this example.
        dummy_value += 1


        # Send out incremented value on arbitrary publication
        # Clear out values published last time
        self.data_to_federation["publications"].clear()
        self.data_to_federation["endpoints"].clear()
        if len(self.data_to_federation["publications"].keys()) >= 1:
            pub = self.hfed.get_publication_by_index(0)
            self.data_to_federation["publications"][pub.name] = dummy_value



    def send_data_to_federation(self):
        """
        This method provides an an easy way for users to send out any data
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
            print(f"publication {key}, {value}")
            pub = self.hfed.get_publication_by_name(key)
            pub.publish(value)

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
        formally destroy a federate. Doing so informs the rest of the
        federation that it is no longer a part of the co-simulation and they
        should proceed without it (if applicable). Generally this is done
        when the co-simulation is complete and all federates end execution
        at more or less the same wall-clock time.

        """
        logger.debug(f'{h.helicsFederateGetName(self.hfed)} being destroyed, max time = {h.HELICS_TIME_MAXTIME}')
        requested_time = int(h.HELICS_TIME_MAXTIME)
        h.helicsFederateClearMessages(self.hfed)
        granted_time = h.helicsFederateRequestTime(self.hfed, requested_time)
        logger.info(f'{h.helicsFederateGetName(self.hfed)} granted time {granted_time}')
        h.helicsFederateDisconnect(self.hfed)
        h.helicsFederateFree(self.hfed)
        # h.helicsCloseLibrary()
        logger.debug(f'Federate {h.helicsFederateGetName(self.hfed)} finalized')


if __name__ == "__main__":
    test_fed = Federate()
    test_fed.connect_to_metadataDB()
    test_fed.create_federate()
    test_fed.run_cosim_loop()
    test_fed.destroy_federate()