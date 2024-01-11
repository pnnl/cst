include(joinpath(dirname(@__FILE__), "..", "cosim_toolbox", "Federate.jl"))
using .Fed

function update_internal_model(obj::Federate)
    # grab data from other federate
    val_to_mult = obj.data_from_federation["inputs"]["jl_fed/add_val"]
    if val_to_mult === Nothing || val_to_mult == -1e+49
        val_to_mult = 1.25
    end
    
    # perform work on model
    val_to_mult = val_to_mult * 3
    
    obj.data_to_federation["publications"]["jl_fed_2/mult_val"] = val_to_mult
end

test_fed = Federate("jl_fed_2")
test_fed.update_internal_model = update_internal_model
test_fed.run_cosim_loop(test_fed)
test_fed.destroy_federate(test_fed)
