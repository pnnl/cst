"""
Created on 12/14/2023

SimpleFederate class that defines the basic operations of 
Python-based logger federate in CoSimulation Toolbox.

@author: Mitch Pelton, Fred Rutz
"""
import sys
import psycopg2

from cosim_toolbox.federate import Federate


def increment_double(original_value):
    if original_value < 0:
        return 0.0
    else:
        return original_value + 1.0


def increment_integer(original_value):
    if original_value < 0:
        return 0
    else:
        return original_value + 1


def increment_complex(original_value):
    if original_value is None:
        original_value = complex(1, 0)
    else:
        x = complex(original_value)
        return str(x + complex(1, 1))


def increment_string(original_value):
    if "-" in original_value:
        return "0"
    else:
        tokens = original_value.split("_")
        t_value = int(tokens[len(tokens) - 1]) + 1
        return original_value + "_" + str(t_value)


def increment_vector(original_value):
    if original_value is None:
        return [0, 1, 2]
    else:
        for i in range(len(original_value)):
            original_value[i] += 1
        t_val = original_value
        return t_val


def increment_complex_vector(original_value):
    if original_value is None:
        t_val = [complex(1, 0), complex(2, 1), complex(3, 2)]
        return t_val
    else:
        for i in range(len(original_value)):
            original_value[i] += complex(1, 1)
        t_val = original_value
        return t_val


def increment_boolean(original_value):
    if original_value is None:
        return True
    else:
        return not original_value


class SimpleFederate(Federate):
    def __init__(self, fed_name="", schema="default", **kwargs):
        super().__init__(fed_name, **kwargs)

    def update_internal_model(self):
        """
        This is entirely user-defined code and is intended to be defined by
        sub-classing and overloading.
        """
        if not self.debug:
            raise NotImplementedError("Subclass from Federate and write code to update internal model")

        for key in self.data_to_federation["publications"]:
            d_type = self.pubs[key]['type'].lower()
            inkey = key.replace("current", "voltage").replace("Battery", "EVehicle")
            dummy = self.data_from_federation["inputs"][inkey]
            if d_type == "double":
                self.data_to_federation["publications"][key] = increment_double(dummy)
            elif d_type == "integer":
                self.data_to_federation["publications"][key] = increment_integer(dummy)
            elif d_type == "complex":
                self.data_to_federation["publications"][key] = increment_complex(dummy)
            elif d_type == "string":
                self.data_to_federation["publications"][key] = increment_string(dummy)
            elif d_type == "vector":
                self.data_to_federation["publications"][key] = increment_vector(dummy)
            elif d_type == "complex vector":
                self.data_to_federation["publications"][key] = increment_complex_vector(dummy)
            elif d_type == "boolean":
                self.data_to_federation["publications"][key] = increment_boolean(dummy)


if __name__ == "__main__":
    if sys.argv.__len__() > 2:
        test_fed = SimpleFederate(sys.argv[1])
        test_fed.create_federate(sys.argv[2])
        test_fed.run_cosim_loop()
        test_fed.destroy_federate()
