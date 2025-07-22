# Obfuscation for Distribution with Pyarmor

## Introduction 

To protect CoSim Toolbox (CST) proprietary code from inadvertent disclosure by licensed parties, CST has been obfuscated through the use of Pyarmor. Pyarmor uses a variety of techniques to transform Python code from a human-readable form to one that is not, thus allowing it to be distributed while securing the intellectual property of the code itself.

More details about the Pyarmor obfuscation process can be found in [its documentation](https://pyarmor.readthedocs.io/en/latest/).

## Obfuscation Process for CST
The obfuscation process using Pyarmor is simple. From the root of the CST repository

```
$ cd src/cosim_toolbox
$ pyrarmor gen cosim_toolbox

```

This generates a folder named "dist" which contains two folders: "cosim_toolbox" and "pyarmor_runtime_000000"; both of these folders are needed to run the now obfuscated CST. 

## Installing Obfuscated CST

Installing the obfuscated CST code is simple:

1. Replace the unobfuscated "cosim_toolbox" folder (the one that was used as the source of the obfuscation) with the one in the "dist" folder (the now obfuscated one). The file name of the Python scripts will be the same between the two folders BUT the contents of the obfuscated ones are no longer human-readable.
2. Move the "pyarmor_runtime_000000" folder to the same level as the "cosim_toolbox" folder you just moved.
3. Run `pip install -e .` from the same folder in which setup.py resides.
4. Install the rest of the CST required libraries by `pip install -r requirements.txt`

## Test Installation

To confirm cosim_toolbox has been installed as a Python package in the current environment, run `pip list` to see cosim_toolbox is listed as an installed package.

To confirm the library is importable (without needing the rest of the CST infrastructure up and running), write and run a simple Python file like:
```
import cosim_toolbox.federate as federate
fed = federate.Federate()
print(fed.stop_time)
# Should return "-1.0" when run.
```

To confirm CST is working as a whole, run the following example. This requires a full, working CST installation.

## TODO

1. What other Python code in the CST repo might we need to obfuscate?


