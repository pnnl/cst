# Copyright (C) 2019-2023 Battelle Memorial Institute
# file: make_include.py
"""Replaces the sphinx-apidoc call because did not want subpackages outline
"""

import os


t_inc = os.path.expandvars('$CST_ROOT/docs/references/cosim_toolbox.inc')
t_api = os.path.expandvars('$CST_ROOT/src/cosim_toolbox/cosim_toolbox')

root = os.path.split(t_api)

with open(t_inc, "w", encoding='utf-8') as fle:
    for dir_name, sub_dirs, files in os.walk(t_api):
        subroot = os.path.split(dir_name)
        if "__" in subroot[1] or "auto_run" in subroot[1]:
            continue

        # root = os.path.split(tesp_api)
        if subroot[1] == root[1]:
            name = subroot[1]
        else:
            name = root[1] + "." + subroot[1]
        name1 = name.replace("_", "\_") + " package"
        print(name1, file=fle)
        print("=" * len(name1), file=fle)
        print("", file=fle)

        print(".. automodule:: " + name, file=fle)
        print("   :members:", file=fle)
        print("   :undoc-members:", file=fle)
        print("   :show-inheritance:", file=fle)
        print("", file=fle)

        print("Submodules", file=fle)
        print("----------", file=fle)
        print("", file=fle)

        files.sort()
        for filename in files:
            if ".py" in filename:
                filename = filename.replace(".py", "")
                if "__" in filename:
                    continue

                if subroot[1] == root[1]:
                    name = subroot[1] + "." + filename
                else:
                    name = root[1] + "." + subroot[1] + "." + filename

                name1 = name.replace("_", "\_") + " module"
                print(name1, file=fle)
                print("-" * len(name1), file=fle)
                print("", file=fle)

                print(".. automodule:: " + name, file=fle)
                print("   :members:", file=fle)
                print("   :undoc-members:", file=fle)
                print("   :show-inheritance:", file=fle)
                print("", file=fle)
