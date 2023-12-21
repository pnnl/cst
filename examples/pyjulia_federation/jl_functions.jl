# using PyCall
# using HELICS
function multiply_value(input::Int64)
    return input*2
end
# # add Copper src code
# pushfirst!(PyVector(pyimport("sys")."path"), "")
# federate = pyimport("Federate")
# test_obj = federate.Federate()
# test_obj.connect_to_metadataDB()
# py"""
# import os
# import sys
# sys.path.insert(1, os.path.join(os.path.dirname(__file__), '..', 'src'))
# from Federate import Federate
# """
# global py_function = py"py_function"