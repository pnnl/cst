============
Introduction
============

Co-Simulation Toolbox to push advances in the field.

Installation
============

cosim_toolbox can be installed using pip_::

  $ pip install cosim_toolbox

However, in order to be useful, cosim_toolbox needs custom versions of
GridLAB-D and other federates that work with HELICS.  It also requires Python 3.10 or later, with
HELICS_, NumPy_, MongoDB_, Pandas_, and Psycopg_.  There is reposistory of the complete
Co-Simulation for Windows, Linux and Mac OS X on GitHub.  A Docker_ version is also available for users.

Development Work Flow for cosim_toolbox
=======================================

* From this directory, 'pip install -e .' points Python to this cloned repository for any calls to cosim_toolbox functions
* See the https://github.com/pnnl/cst for a roadmap of existing Python source files, and some documentation.  Any changes or additions to the code need to be made in this directory.
* Run tests from any other directory on this computer
* When ready, edit the cosim_toolbox version number and dependencies in setup.py
* To deploy follow the instructions in the Python Packaging Guide:
    1. Create an account on PyPI if you haven't yet.
    2. Install twine and build: pip install twine build
    3. Create the source distribution, change to 'src' directory execute: python3 -m build .
    4. Check your distribution files for errors: twine check dist/*
    5. (Optional) Upload to the PyPI test server first (note: separate user registration required): twine upload --repository-url https://test.pypi.org/legacy/ dist/*
    6. Upload to PyPI: twine upload dist/*
* Any user gets the changes with 'pip install cosim_toolbox --upgrade'
* Use 'pip show cosim_toolbox' to verify the version and location on your computer

Using Co-Simulation Toolbox
===========================

This is a developer's platform for electric power grid research.  See
http://cosimtoolbox.readthedocs.io/en/latest/ for user instructions, and
https://[github]/copper for source code.

Links to Dependencies
=====================

* Docker_
* GridLAB-D_
* HELICS_
* NumPy_
* MongoDB_
* Pandas_
* Psycopg_
* Python_

Subdirectories
==============

- *cosim_toolbox*; utilities for building and running co-simulations using HELICS federates.
- *test*; scripts that support testing the package; not automated.

License & Copyright
===================

- Copyright (c) 2022-2025 Battelle Memorial Institute

.. _Docker: https://www.docker.com
.. _GridLAB-D: http://gridlab-d.shoutwiki.com
.. _HELICS: https://helics.org
.. _NumPy: https://www.numpy.org
.. _MongoDB: https://www.mongodb.com
.. _Pandas: https://pandas.pydata.org
.. _Psycopg: https://www.psycopg.org/docs
.. _pip: https://pip.pypa.io/en/stable
.. _Python: https://www.python.org