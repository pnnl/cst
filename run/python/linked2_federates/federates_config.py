"""
Created on 7/7/2023

@author: Mitch Pelton
mitch.pelton@pnnl.gov
"""

import gridlabd_output
import substation_output
import pypower_output
import weather_output
from cosim_toolbox.federation import FederateConfig
from cosim_toolbox.federation import FederationConfig
from cosim_toolbox.dockerRunner import DockerRunner
from tesp_support.api.modify_GLM import GLMModifier


# Format
# {
#     "from_fed":  string -> name of the publisher
#     "to_fed":  string -> name of the subscriber
#     "fed":  string -> name of the publisher in the helics configuration file
#     "datatype": string -> any valid data [double, integer, boolean, string, complex, json]
#     "info": boolean -> if "True" split out the property value and code the info object
#                        else code no info object
#     if "keys" and "indices" are missing, we are likely using add_subs or add_group_subs
#     "keys": [
#         string -> used for the generation for name(s), using for @@ ## pair, @list@, @@ in the replacement,
#         string -> the 'object' used in the 'info' field using, using for  @@ ## pair, @list@, @@ in the replacement
#     ]
#     "indices": [  // one of the following formats, and can have multiples [],[]...
#        // for replacement @@ ## pair
#        [
#           string -> used for the replacement @@,
#           integer -> starting number, inclusive,
#           integer -> ending number, exclusive
#        ],
#        // for replacement @@
#        [
#           string -> used for the replacement @@,
#           boolean -> if "True" do not append the group name in the replacement
#                       else append the group name in the replacement
#        ],
#        // for replacement ##
#        [
#           integer -> starting number, inclusive,
#           integer -> ending number, exclusive,
#           boolean -> if "True" not append the federate replacement
#                       else append the federate the replacement
#        ],
#        // for replacement @list@
#        [
#           string(s) -> comma separated list used for the replacement
#        ],
#        // no indices, single,  no bracket needed
#     ]
# }

def get_names(path: str) -> dict:
    my_glm = GLMModifier()
    glm, success = my_glm.read_model(path)
    if not success:
        print(f'{path} not found or file not supported; exiting')
    fmt = {
        "house": {"from_fed": "gld_7", "fed": "", "keys": ["@list@", "@list@"], "indices": []},
        "meter": {"from_fed": "gld_7", "fed": "", "keys": ["@list@", "@list@"], "indices": []},
        "hvac": {"from_fed": "sub_7", "fed": "", "keys": ["@list@", ""], "indices": []},
        "billing": {"from_fed": "sub_7", "fed": "", "keys": ["@list@", ""], "indices": []}
    }
    for name, attr in glm.house.items():
        if 'ELECTRIC' in attr["cooling_system_type"]:
            fmt["house"]["indices"].append(name)
            fmt["meter"]["indices"].append(attr["parent"])
            fmt["hvac"]["indices"].append(name)
            fmt["billing"]["indices"].append(name + "/" + attr["parent"])
    return fmt

def define_federation_list():
    with_docker = False
    names = ["gld_7", "sub_7", "pypower", "localWeather"]

    gld_fmt = get_names("test.glm")

    # gridlabd
    load = {"src": {"from_fed": names[0],
                    "keys": ["", "network_node"],
                    "indices": []},
            "des": [{"to_fed": names[1],
                     "from_fed": names[0]}]}
    house = {"src": gld_fmt["house"],
             "des": [{"to_fed": names[1],
                      "from_fed": names[0] }]}
    meter = {"src": gld_fmt["meter"],
             "des": [{"to_fed": names[1],
                      "from_fed": names[0] }]}
    # substation
    hvac = {"src": gld_fmt["hvac"],
            "des": [{"to_fed": names[0],
                     "from_fed": names[1],
                     "info": True}]}
    billing = {"src": gld_fmt["billing"],
               "des": [{"to_fed": names[0],
                        "from_fed": names[1],
                        "info": True}]}
    bid = {"src": {"from_fed": names[1],
                   "keys": ["", ""],
                   "indices": []},
           "des": [{"to_fed": names[2],
                    "from_fed": names[1],
                    "keys": ["", ""],
                    "indices": []}]}
    # pypower
    lmp = {"src": {"from_fed": names[2],
                   "keys": ["", ""],
                   "indices": []},
           "des": [{"to_fed": names[1],
                    "from_fed": names[2],
                    "keys": ["", ""],
                    "indices": []}]}
    voltage = {"src": {"from_fed": names[2],
                       "keys": ["", ""],
                       "indices": []},
               "des": [{"to_fed": names[0],
                        "from_fed": names[2],
                        "keys": ["@@", "network_node"],
                        "indices": [["three_phase_voltage_7", True]]
                        }]}
    # weather
    weather = {"src": {"from_fed": names[3]},
               "des": [{"to_fed": names[0],
                        "from_fed": names[3],
                        "keys": ["#", "localWeather"],
                        "indices": []}]}

    federation = FederationConfig("MyLink2Scenario", "MyLink2analysis", "MyLink2Federation", with_docker)
    f1 = federation.add_federate_config(FederateConfig(names[0], period=15))
    f2 = federation.add_federate_config(FederateConfig(names[1], period=15))
    f3 = federation.add_federate_config(FederateConfig(names[2], period=15))
    f4 = federation.add_federate_config(FederateConfig(names[3], period=300))

    # addGroup from the perspective what is published
    # gridlabd
    federation.add_group("distribution_load", "complex", load)
    federation.add_group("power_state", "string", house)
    federation.add_group("air_temperature", "double", house)
    federation.add_group("hvac_load", "double", house)
    federation.add_group("measured_voltage_1", "complex", meter)
    # substation
    federation.add_group("cooling_setpoint", "double", hvac)
    federation.add_group("heating_setpoint", "double", hvac)
    federation.add_group("thermostat_deadband", "double", hvac)
    federation.add_group("bill_mode", "string", billing)
    federation.add_group("price", "double", billing)
    federation.add_group("monthly_fee", "double", billing)
    federation.add_group("unresponsive_mw", "double", bid)
    federation.add_group("responsive_max_mw", "double", bid)
    federation.add_group("responsive_c2", "double", bid)
    federation.add_group("responsive_c1", "double", bid)
    federation.add_group("responsive_deg", "integer", bid)
    federation.add_group("clear_price", "double", bid)
    # pypower
    federation.add_group("LMP_7", "double", lmp)
    federation.add_group("three_phase_voltage_7", "double", voltage)
    # weather
    federation.add_group("temperature", "double", weather)
    federation.add_group("humidity", "double", weather)
    federation.add_group("solar_direct", "double", weather)
    federation.add_group("solar_diffuse", "double", weather)
    federation.add_group("pressure", "double", weather)
    federation.add_group("wind_speed", "double", weather)
    federation.define_io()

    missing = federation.check_pubs()
    print("pubs-> ", missing)
    missing = federation.check_subs()
    print("subs-> ", missing)

    if with_docker:
        f1.config("image", "cosim-cst:latest")
        f2.config("image", "cosim-cst:latest")
        f3.config("image", "cosim-cst:latest")
        f4.config("image", "cosim-cst:latest")

    f1.config("command", f"gridlabd -D USE_HELICS -D METRICS_FILE=test_metrics.json test.glm")
    f2.config("command", f"python3 -c \"import tesp_support.api.substation as tesp;tesp.substation_loop('test_agent_dict.json','test',helicsConfig='{names[1]}.json')\"")
    f3.config("command", f"python3 -c \"import tesp_support.api.tso_PYPOWER as tesp;tesp.tso_pypower_loop('test_pp.json','test',helicsConfig='{names[2]}.json')\"")
    f4.config("prefix", "export WEATHER_CONFIG=test_weather.json")
    f4.config("command", f"python3 -c \"import tesp_support.weather.weather_agent as tesp;tesp.startWeatherAgent('weather.dat')\"")

    federation.write_config("2023-12-07T15:31:27", "2023-12-08T15:31:27")
    DockerRunner.define_sh("MyLink2Scenario")

def define_federation():
    with_docker = False
    names = ["gld_7", "sub_7", "pypower", "localWeather"]

    # gridlabd
    load = {"src": {"from_fed": names[0],
                    "keys": ["", "network_node"],
                    "indices": []},
            "des": [{"to_fed": names[1],
                     "from_fed": names[0],
                     "keys": ["", ""],
                     "indices": []
                     }]}
    house = {"src": {"from_fed": names[0],
                     "keys": ["Fdr1_Houses_@@_hse_##", "Fdr1_Houses_@@_hse_##"],
                     "indices": [["A", 1, 501], ["B", 1, 501], ["C", 1, 501]]},
             "des": [{"to_fed": names[1],
                      "from_fed": names[0],
                      "keys": ["Fdr1_Houses_@@_hse_##", ""],
                      "indices": [["A", 1, 501], ["B", 1, 501], ["C", 1, 501]]
                      }]}
    meter = {"src": {"from_fed": names[0],
                     "keys": ["Fdr1_Houses_@@_mhse_##", "Fdr1_Houses_@@_mhse_##"],
                     "indices": [["A", 1, 501], ["B", 1, 501], ["C", 1, 501]]},
             "des": [{"to_fed": names[1],
                      "from_fed": names[0],
                      "keys": ["Fdr1_Houses_@@_mhse_##", ""],
                      "indices": [["A", 1, 501], ["B", 1, 501], ["C", 1, 501]]
                      }]}
    # substation
    hvac = {"src": {"from_fed": names[1],
                    "keys": ["Fdr1_Houses_@@_hse_##", ""],
                    "indices": [["A", 1, 501], ["B", 1, 501], ["C", 1, 501]]},
            "des": [{"to_fed": names[0],
                     "from_fed": names[1],
                     "keys": ["Fdr1_Houses_@@_hse_##", "Fdr1_Houses_@@_hse_##"],
                     "indices": [["A", 1, 501], ["B", 1, 501], ["C", 1, 501]]
                     }]}
    billing = {"src": {"from_fed": names[1],
                       "keys": ["Fdr1_Houses_@@_hse_##/Fdr1_Houses_@@_mhse_##", ""],
                       "indices": [["A", 1, 501], ["B", 1, 501], ["C", 1, 501]]},
               "des": [{"to_fed": names[0],
                        "from_fed": names[1],
                        "keys": ["Fdr1_Houses_@@_hse_##/Fdr1_Houses_@@_mhse_##", "Fdr1_Houses_@@_mhse_##"],
                        "indices": [["A", 1, 501], ["B", 1, 501], ["C", 1, 501]]
                        }]}
    bid = {"src": {"from_fed": names[1],
                   "keys": ["", ""],
                   "indices": []},
           "des": [{"to_fed": names[2],
                    "from_fed": names[1],
                    "keys": ["", ""],
                    "indices": []}]}
    # pypower
    lmp = {"src": {"from_fed": names[2],
                   "keys": ["", ""],
                   "indices": []},
           "des": [{"to_fed": names[1],
                    "from_fed": names[2],
                    "keys": ["", ""],
                    "indices": []}]}
    voltage = {"src": {"from_fed": names[2],
                       "keys": ["", ""],
                       "indices": []},
               "des": [{"to_fed": names[0],
                        "from_fed": names[2],
                        "keys": ["@@", "network_node"],
                        "indices": [["three_phase_voltage_7", True]]
                        }]}
    # weather
    weather = {"src": {"from_fed": names[3]},
               "des": [{"to_fed": names[0],
                        "from_fed": names[3],
                        "keys": ["#", "localWeather"],
                        "indices": []}]}

    federation = FederationConfig("MyLink2Scenario", "MyLink2analysis", "MyLink2Federation", with_docker)
    f1 = federation.add_federate_config(FederateConfig(names[0], period=15))
    f2 = federation.add_federate_config(FederateConfig(names[1], period=15))
    f3 = federation.add_federate_config(FederateConfig(names[2], period=15))
    f4 = federation.add_federate_config(FederateConfig(names[3], period=300))

    # addGroup from the perspective what is published
    # gridlabd
    federation.add_group("distribution_load", "complex", load)
    federation.add_group("power_state", "string", house)
    federation.add_group("air_temperature", "double", house)
    federation.add_group("hvac_load", "double", house)
    federation.add_group("measured_voltage_1", "complex", meter)
    # substation
    federation.add_group("cooling_setpoint", "double", hvac)
    federation.add_group("heating_setpoint", "double", hvac)
    federation.add_group("thermostat_deadband", "double", hvac)
    federation.add_group("bill_mode", "string", billing)
    federation.add_group("price", "double", billing)
    federation.add_group("monthly_fee", "double", billing)
    federation.add_group("unresponsive_mw", "double", bid)
    federation.add_group("responsive_max_mw", "double", bid)
    federation.add_group("responsive_c2", "double", bid)
    federation.add_group("responsive_c1", "double", bid)
    federation.add_group("responsive_deg", "integer", bid)
    federation.add_group("clear_price", "double", bid)
    # pypower
    federation.add_group("LMP_7", "double", lmp)
    federation.add_group("three_phase_voltage_7", "double", voltage)
    # weather
    federation.add_group("temperature", "double", weather)
    federation.add_group("humidity", "double", weather)
    federation.add_group("solar_direct", "double", weather)
    federation.add_group("solar_diffuse", "double", weather)
    federation.add_group("pressure", "double", weather)
    federation.add_group("wind_speed", "double", weather)
    federation.define_io()

    missing = federation.check_pubs()
    print("pubs-> ", missing)
    missing = federation.check_subs()
    print("subs-> ", missing)
    if with_docker:
        f1.config("image", "cosim-cst:latest")
        f2.config("image", "cosim-cst:latest")
        f3.config("image", "cosim-cst:latest")
        f4.config("image", "cosim-cst:latest")

    f1.config("command", f"gridlabd -D USE_HELICS -D METRICS_FILE=test_metrics.json test.glm")
    f2.config("command", f"python3 -c \"import tesp_support.api.substation as tesp;tesp.substation_loop('test_agent_dict.json','test',helicsConfig='{names[1]}.json')\"")
    f3.config("command", f"python3 -c \"import tesp_support.api.tso_PYPOWER as tesp;tesp.tso_pypower_loop('test_pp.json','test',helicsConfig='{names[2]}.json')\"")
    f4.config("prefix", "export WEATHER_CONFIG=test_weather.json")
    f4.config("command", f"python3 -c \"import tesp_support.weather.weather_agent as tesp;tesp.startWeatherAgent('weather.dat')\"")

    federation.write_config("2023-12-07T15:31:27", "2023-12-08T15:31:27")
    DockerRunner.define_sh("MyLink2Scenario")

def define_match():
    with_docker = False
    names = ["gld_7", "sub_7", "pypower", "localWeather"]
    federation = FederationConfig("MyLink2Scenario", "MyLink2analysis", "MyLink2Federation", with_docker)

    federation.add_federate_config(gridlabd_output.MyFederateMatch(names[0], period=15))
    federation.add_federate_config(substation_output.MyFederateMatch(names[1], period=15))
    federation.add_federate_config(pypower_output.MyFederateMatch(names[2], period=15))
    federation.add_federate_config(weather_output.MyFederate(names[3], period=300))
    federation.add_subs(names[0],[names[1], names[2]],True)
    federation.add_subs(names[1],[names[0], names[2]],False)
    federation.add_subs(names[2],[names[1]],False)
    federation.define_io()

    missing = federation.check_pubs()
    print("pubs-> ", missing)
    missing = federation.check_subs()
    print("subs-> ", missing)

    federation.write_config("2023-12-07T15:31:27", "2023-12-08T15:31:27")
    DockerRunner.define_sh("MyLink2Scenario")

def define_format():
    with_docker = False
    names = ["gld_7", "sub_7", "pypower", "localWeather"]
    federation = FederationConfig("MyLink2Scenario", "MyLink2Schema", "MyLink2Federation", with_docker)

    federation.add_federate_config(gridlabd_output.MyFederate(names[0], period=15))
    federation.add_federate_config(substation_output.MyFederate(names[1], period=15))
    federation.add_federate_config(pypower_output.MyFederate(names[2], period=15))
    federation.add_federate_config(weather_output.MyFederate(names[3], period=300))
    federation.define_io()

    missing = federation.check_pubs()
    print("pubs-> ", missing)
    missing = federation.check_subs()
    print("subs-> ", missing)

    federation.write_config("2023-12-07T15:31:27", "2023-12-08T15:31:27")
    DockerRunner.define_sh("MyLink2Scenario")

if __name__ == "__main__":
    # define_format()
    # define_match()
    # define_federation()
    define_federation_list()