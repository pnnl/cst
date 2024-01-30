module db
    global MAX_TIME = 5
    global py_federate_dict = Dict(
        "image"=> "nothing_pth",
        "federate type"=> "value",
        "sim step size"=> 1,
        "max sim time"=> MAX_TIME,
        "HELICS config"=>Dict(
        "name"=> "py_fed",
        "core_type"=> "zmq",
        "log_level"=> "warning",
        "period"=> 1,
        "uninterruptible"=> false,
        "terminate_on_error"=> true,
        "publications"=> [
            Dict(
            "global"=> true,
            "key"=> "py_fed/add_val",
            "type"=> "double"
            )
        ],
        "subscriptions"=> [
            Dict(
                "global"=> true,
                "key"=> "jl_fed/mult_val",
                "type"=> "double"
            )
        ]
        )
    )

    global jl_federate_dict = Dict(
        "image"=> "nothing_pth",
        "federate type"=> "value",
        "sim step size"=> 1,
        "max sim time"=> MAX_TIME,
        "HELICS config"=> Dict(
        "name"=> "jl_fed",
        "core_type"=> "zmq",
        "log_level"=> "warning",
        "period"=> 1,
        "uninterruptible"=> false,
        "terminate_on_error"=> true,
        "publications"=> [
            Dict(
            "global"=> true,
            "key"=> "jl_fed/add_val",
            "type"=> "double"
            )
        ],
        "subscriptions"=>[
            Dict(
                "global"=>true,
                "key"=>"jl_fed_2/mult_val",
                "type"=>"double"
            )
        ]
        )
    )

    global jl_federate_dict_2 = Dict(
        "image"=> "nothing_pth",
        "federate type"=> "value",
        "sim step size"=> 1,
        "max sim time"=> MAX_TIME,
        "HELICS config"=> Dict(
        "name"=> "jl_fed_2",
        "core_type"=> "zmq",
        "log_level"=> "warning",
        "period"=> 1,
        "uninterruptible"=> false,
        "terminate_on_error"=> true,
        "publications"=> [
            Dict(
            "global"=> true,
            "key"=> "jl_fed_2/mult_val",
            "type"=> "double"
            )
        ],
        "subscriptions"=>[
            Dict(
                "global"=>true,
                "key"=>"jl_fed/add_val",
                "type"=>"double"
            )
        ]
        )
    )
    # "publications"=> [
    #     Dict(
    #     "global"=> true,
    #     "key"=> "jl_fed/mult_val",
    #     "type"=> "double"
    #     )
    # ],
    # "subscriptions"=> [
    #     Dict(
    #         "global"=> true,
    #         "key"=> "py_fed/add_val",
    #         "type"=> "double"
    #     )
    # ]

    global federation_dict = Dict(
        "name"=> "test_federation",
        "max sim time"=> MAX_TIME,
        "broker"=> true,
        "federates"=> [

        Dict(
            "directory"=> ".",
            "host"=> "localhost",
            "name"=> "jl_fed"
        ),
        Dict(
            "directory"=> ".",
            "host"=> "localhost",
            "name"=> "jl_fed_2"
        )
        ],
        "py_fed"=> py_federate_dict,
        "jl_fed"=> jl_federate_dict,
        "jl_fed_2" => jl_federate_dict_2
    )
    # Dict(
    #     "directory"=> ".",
    #     "host"=> "localhost",
    #     "name"=> "py_fed"
    # ),

    global scenario_dict = Dict(
        "current scenario" => "test_federation"
    )

    global test_dictionaries = Dict("current scenario" => scenario_dict, "federation" => federation_dict)

    export get_dict
    function get_dict(dict_name::String)
        return test_dictionaries[dict_name]
    end

end