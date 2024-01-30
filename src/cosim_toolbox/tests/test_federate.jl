using HELICS
include(joinpath(dirname(@__FILE__), "..", "cosim_toolbox", "Federate.jl"))
using .Fed

function update_internal_model(obj::Federate)
    # grab data from other federate
    val_to_add = obj.data_from_federation["inputs"]["jl_fed_2/mult_val"]
    if val_to_add === nothing || val_to_add == -1e+49
        val_to_add = 1.5
    end
    
    # perform work on model
    val_to_add += 1
    
    obj.data_to_federation["publications"]["jl_fed/add_val"] = val_to_add
end

test_fed = Federate("jl_fed")
test_fed.update_internal_model = update_internal_model

broker = HELICS.helicsCreateBroker("zmq", "mainbroker", "-f 2")
test_fed.run_cosim_loop(test_fed)
test_fed.destroy_federate(test_fed)
