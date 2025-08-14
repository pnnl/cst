import os

from cosim_toolbox.federate import Federate
from julia import Main

Main.include(os.path.join(os.path.dirname(__file__), "jl_functions.jl"))


# create two federate classes with their own step functions
class Python_Fed(Federate):

    def update_internal_model(self):
        # grab data from other federate
        val_to_add = self.data_from_federation['inputs']['pyjl_fed/mult_val']
        if val_to_add == None or val_to_add == -1e+49:
            val_to_add = 1

        # perform work on model
        val_to_add += 1

        self.data_to_federation['publications']['py_fed/add_val'] = val_to_add


class PyJulia_Fed(Federate):

    def update_internal_model(self):
        # grab data from other federate
        val_to_mult = self.data_from_federation['inputs']['py_fed/add_val']
        if val_to_mult == None or val_to_mult == -1e+49:
            val_to_mult = 1

        # perform work on model
        val_to_mult = Main.multiply_value(val_to_mult)

        self.data_to_federation['publications']['pyjl_fed/mult_val'] = val_to_mult
