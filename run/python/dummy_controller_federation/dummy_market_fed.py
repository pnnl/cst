"""
Created on 3/11/2024

DummyMarketFederate class defines a dummy market that
will send dummy data to the federation, to test the dummy controller.

@author: Shat Pratoomratana
shat.pratoomratana@pnnl.gov
"""
import sys
from cosim_toolbox.federate import Federate
import json

def DAM_clearing_info():
    market_info = {
    "cleared quantities":
        [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    "cleared prices": 
        [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
                    }
    
    return market_info
    
def frequency_clearing_info():
    market_info = {
    "cleared quantities":
        [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    "cleared prices": 
        [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
                    }
    
    return market_info

def realtime_clearing_info():
    market_info = {
    "cleared quantities": 0,
    "cleared prices": 0
                    }
    
    return market_info




class DummyMarketFederate(Federate):
    
    def __init__(self, fed_name="", schema="default", **kwargs):
        super().__init__(fed_name, **kwargs)
        
    
    #Overload update_internal_model(self): function in the Federate class for the functions I need    
    def update_internal_model(self):
        """
        This is entirely user-defined code and is intended to be defined by
        sub-classing and overloading.
        """
        if not self.debug:
            raise NotImplementedError("Subclass from Federate and write code to update internal model")
        
        #keys for publications
        DAM_pub_key = "Market/DAM_clearing_info"
        freq_pub_key = "Market/frequency_clearing_info"
        realtime_pub_key = "Market/realtime_clearing_info"
        #keys for the subscriptions
        DAM_sub_key = "Controller/DAM_bid"
        freq_sub_key = "Controller/frequency_bid"
        realtime_sub_key = "Controller/realtime_bid"
       
    
        #get bid information from the controller federate via HELICS
        DAM_bid_info = json.loads(self.data_from_federation["inputs"][DAM_sub_key])
        freq_bid_info = json.loads(self.data_from_federation["inputs"][freq_sub_key])
        realtime_bid_info = json.loads(self.data_from_federation["inputs"][realtime_sub_key])
        print(DAM_bid_info)

        #Create market clearing information then send them out via HELICS
        self.data_to_federation["publications"][DAM_pub_key] = json.dumps(DAM_clearing_info())
        self.data_to_federation["publications"][freq_pub_key] = json.dumps(frequency_clearing_info())
        self.data_to_federation["publications"][realtime_pub_key] = json.dumps(realtime_clearing_info())

        # return super().update_internal_model()
    
        
if __name__ == "__main__":
    if sys.argv.__len__() > 2:
        test_fed = DummyMarketFederate(sys.argv[1])
        test_fed.run(sys.argv[2])
    