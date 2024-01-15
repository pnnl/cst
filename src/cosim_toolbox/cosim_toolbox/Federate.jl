"""
Currently uses temp_jl_db to pull federate information until metadataDB can be successfully converted to julia.
"""
module Fed
    using JSON
    using HELICS
    include(joinpath(dirname(@__FILE__), "temp_jl_db.jl"))
    using .db

    export Federate
    mutable struct Federate
        hfed::Union{Nothing, HELICS.ValueFederate, HELICS.MessageFederate, HELICS.CombinationFederate}
        # mddb::Union{Nothing, MetaDB}
        main_collection::String
        fed_name::String
        sim_step_size::Int
        max_sim_time::Int
        next_requested_time::Int
        granted_time::Int
        data_from_federation::Dict{String, Dict{String, Union{Nothing, Int, String, Float64}}}
        data_to_federation::Dict{String, Dict{String, Union{Nothing, Int, String, Float64}}}
        inputs::Dict{String, Dict}
        pubs::Dict{String, Dict}
        endpoints::Dict{String, Dict}
        debug::Bool
        connect_to_metadataDB::Function
        determine_input_function::Function
        determine_publication_function::Function
        create_federate::Function
        initialize_fed::Function
        create_helics_fed::Function
        run_cosim_loop::Function
        enter_initialization::Function
        enter_executing_mode::Function
        simulate_next_step::Function
        calculate_next_requested_time::Function
        request_time::Function
        get_data_from_federation::Function
        update_internal_model::Function
        send_data_to_federation::Function
        destroy_federate::Function

    end

    export Federate
    function Federate(fed_name::String, kwargs...)
        fed = Federate(
            nothing, "main", fed_name, -1, -1, -1, -1, Dict(), Dict(),
            Dict(), Dict(), Dict(), true, connect_to_metadataDB, determine_input_function, determine_publication_function,
            create_federate, initialize_fed, 
            create_helics_fed, run_cosim_loop, enter_initialization, enter_executing_mode, simulate_next_step, calculate_next_requested_time,
            request_time,  get_data_from_federation, update_internal_model, send_data_to_federation, destroy_federate, kwargs...
        )
        fed.data_from_federation["inputs"] = Dict()
        fed.data_from_federation["endpoints"] = Dict()
        fed.data_to_federation["publications"] = Dict()
        fed.data_to_federation["endpoints"] = Dict()
        return fed
    end

    export determine_input_function
    function determine_input_function(put::HELICS.Input)
        input_type = HELICS.helicsInputGetType(put)
        input_getter_dict = Dict{String, Function}("boolean"=>HELICS.helicsInputGetBoolean,
        "char"=>HELICS.helicsInputGetChar, "complex"=>HELICS.helicsInputGetComplex,
         "double"=>HELICS.helicsInputGetDouble, "integer"=>HELICS.helicsInputGetInteger,
          "string"=>HELICS.helicsInputGetString,"vector"=>HELICS.helicsInputGetVector)
        return input_getter_dict[input_type](put)
    end

    export determine_publication_function
    function determine_publication_function(pub::HELICS.Publication, val)
        pub_type = HELICS.helicsPublicationGetType(pub)
        publication_getter_dict = Dict{String, Function}("boolean"=>HELICS.helicsPublicationPublishBoolean,
        "char"=>HELICS.helicsPublicationPublishChar, "complex"=>HELICS.helicsPublicationPublishComplex,
        "double"=>HELICS.helicsPublicationPublishDouble, "integer"=>HELICS.helicsPublicationPublishInteger,
        "string"=>HELICS.helicsPublicationPublishString,"vector"=>HELICS.helicsPublicationPublishVector)
        return publication_getter_dict[pub_type](pub, val)
    end

    export connect_to_metadataDB
    function connect_to_metadataDB(obj::Federate)
        # TODO: connect to metadb object
        obj.mddb = MetaDB(uri=uri)
    end

    export create_federate
    function create_federate(obj::Federate)
        scenario_name = obj.create_helics_fed(obj)
        obj.initialize_fed(obj, scenario_name)
    end

    export initialize_fed
    function initialize_fed(obj::Federate, scenario_name::String)
        fed_dict = db.get_dict("federation")[obj.fed_name]
        helics_dict = fed_dict["HELICS config"]
        obj.sim_step_size = fed_dict["sim step size"]
        obj.max_sim_time = db.get_dict("federation")["max sim time"]

        if "publications" in keys(helics_dict)
            for pub in helics_dict["publications"]
                obj.data_to_federation["publications"][pub["key"]] = nothing
            end
        end

        if "inputs" in keys(helics_dict)
            for inp in helics_dict["inputs"]
                obj.data_from_federation["inputs"][inp["key"]] = nothing
            end
        end

        if "subscriptions" in keys(helics_dict)
            for inp in helics_dict["subscriptions"]
                obj.data_from_federation["inputs"][inp["key"]] = nothing
            end
        end

        if "endpoints" in keys(helics_dict)
            for ep in helics_dict["endpoints"]
                if "key" in keys(ep)
                    obj.data_to_federation["endpoints"][ep["key"]] = nothing
                end

                if "destination" in keys(ep)
                    obj.data_from_federation["endpoints"][ep["key"]] = nothing
                end
            end
        end
    end

    export create_helics_fed
    function create_helics_fed(obj::Federate)
        scenario_name = db.get_dict("current scenario")["current scenario"]
        fed_def = db.get_dict("federation")[obj.fed_name]

        if fed_def["federate type"] == "value"
            obj.hfed = HELICS.helicsCreateValueFederateFromConfig(JSON.json(fed_def["HELICS config"]))
        elseif fed_def["federate type"] == "message"
            obj.hfed = HELICS.helicsCreateMessageFederateFromConfig(JSON.json(fed_def["HELICS config"]))
        elseif fed_def["federate type"] == "combo"
            obj.hfed = HELICS.helicsCreateCombinationFederateFromConfig(JSON.json(fed_def["HELICS config"]))
        else
            throw(ErrorException("Federate type $(fed_def["federate type"]) not allowed; must be 'value', 'message', or 'combo'."))
        end

        if obj.debug
            if "publications" in keys(fed_def["HELICS config"])
                for pub in fed_def["HELICS config"]["publications"]
                    obj.pubs[pub["key"]] = pub
                end
            end

            if "subscriptions" in keys(fed_def["HELICS config"])
                for sub in fed_def["HELICS config"]["subscriptions"]
                    obj.inputs[sub["key"]] = sub
                end
            end

            if "inputs" in keys(fed_def["HELICS config"])
                for put in fed_def["HELICS config"]["inputs"]
                    obj.inputs[put["name"]] = put
                end
            end

            if "endpoints" in keys(fed_def["HELICS config"])
                for ep in fed_def["HELICS config"]["endpoints"]
                    obj.endpoints[ep["name"]] = ep
                end
            end
        end

        return scenario_name
    end

    export run_cosim_loop
    function run_cosim_loop(obj::Federate)
        if obj.hfed === nothing
            obj.create_federate(obj)
        end

        obj.granted_time = 0
        obj.enter_initialization(obj)
        obj.enter_executing_mode(obj)

        while obj.granted_time < obj.max_sim_time
            obj.simulate_next_step(obj)
        end

    end

    export enter_initialization
    function enter_initialization(obj::Federate)
        HELICS.helicsFederateEnterInitializingMode(obj.hfed)
    end

    export enter_executing_mode
    function enter_executing_mode(obj::Federate)
        HELICS.helicsFederateEnterExecutingMode(obj.hfed)
    end

    export simulate_next_step
    function simulate_next_step(obj::Federate)
        next_requested_time = obj.calculate_next_requested_time(obj)
        obj.request_time(obj, next_requested_time)
        obj.get_data_from_federation(obj)
        obj.update_internal_model(obj)
        obj.send_data_to_federation(obj)
    end

    export calculate_next_requested_time
    function calculate_next_requested_time(obj::Federate)
        obj.next_requested_time = obj.granted_time + obj.sim_step_size
        return obj.next_requested_time
    end

    export request_time
    function request_time(obj::Federate, requested_time::Int)
        obj.granted_time = HELICS.helicsFederateRequestTime(obj.hfed, requested_time)
    end

    export get_data_from_federation
    function get_data_from_federation(obj::Federate)
        for idx in 0:HELICS.helicsFederateGetInputCount(obj.hfed) - 1
            put = HELICS.helicsFederateGetInputByIndex(obj.hfed, idx)
            input_name = HELICS.helicsInputGetName(put)
            input_target = HELICS.helicsInputGetTarget(put)
            input_val = obj.determine_input_function(put)
            if occursin("_input_", input_name)
                obj.data_from_federation["inputs"][input_target] = input_val
            else
                obj.data_from_federation["inputs"][input_name] = input_val
            end
        end

        for idx in 0:HELICS.helicsFederateGetEndpointCount(obj.hfed) - 1
            ep = HELICS.helicsFederateGetEndpointByIndex(obj.hfed, idx)
            ep_name = HELICS.helicsEndpointGetName(ep)
            obj.data_from_federation[ep_name] = []

            for message in 0:HELICS.helicsEndpointPendingMessageCount(ep)
                push!(obj.data_from_federation["endpoints"][ep_name], HELICS.helicsEndpointGetMessage(ep))
            end
        end
    end

    export update_internal_model
    function update_internal_model(obj::Federate)
        if !obj.debug
            throw(NotImplementedError("Subclass from Federate and write code to update internal model"))
        end

        if length(keys(obj.data_from_federation["inputs"])) >= 1
            key = first(keys(obj.data_from_federation["inputs"]))
            dummy_value = obj.data_from_federation["inputs"][key]
        else
            dummy_value = 0
        end

        dummy_value += 1

        for pub in keys(obj.data_to_federation["publications"])
            obj.data_to_federation["publications"][pub] = nothing
        end

        for ep in keys(obj.data_to_federation["endpoints"])
            obj.data_to_federation["endpoints"][ep] = nothing
        end

        if length(keys(obj.data_to_federation["publications"])) >= 1
            pub = HELICS.helicsFederateGetPublicationByIndex(obj.hfed, 0)
            pub_name = HELICS.helicsPublicationGetName(pub)
            obj.data_to_federation["publications"][pub_name] = dummy_value
        end
    end

    export send_data_to_federation
    function send_data_to_federation(obj::Federate)
        for (key, value) in obj.data_to_federation["publications"]
            pub = HELICS.helicsFederateGetPublication(obj.hfed, key)
            obj.determine_publication_function(pub, value)
        end

        for (key, value) in obj.data_to_federation["endpoints"]
            ep = HELICS.helicsGetEndpointByName(obj.hfed, key)

            if value["destination"] == ""
                HELICS.helicsEndpointSendData(ep, value["payload"])
            else
                HELICS.helicsEndpointSendData(ep, value["payload"], value["destination"])
            end
        end
    end

    export destroy_federate
    function destroy_federate(obj::Federate)
        requested_time = trunc(Int, HELICS.HELICS_TIME_MAXTIME)
        HELICS.helicsFederateClearMessages(obj.hfed)
        granted_time = HELICS.helicsFederateRequestTime(obj.hfed, requested_time)
        HELICS.helicsFederateDisconnect(obj.hfed)
        HELICS.helicsFederateFree(obj.hfed)
    end
    
end
