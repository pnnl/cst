# Installing CoSim Toolbox
**TODO** - Likely need to modify the scripting to allow us to install the persistent services separately from the CST image. Do users need to install the CST image to stand-up the persistent services?


The installation of CoSim Toolbox (CST) will vary on how the co-simulation is expected to be run. In fact, there are a number of different installation and configuration styles dependent on what type of functionality CST is intended to supply. CST generally provides multiple forms of support tooling

1. Persistent services - These are services that will remain running all the time and are usable by any CST-based co-simulation. Generally, these are the services responsible for workflow management, metadata management, data collection and data presentation. 
2. APIs - CST provides Python APIs for accessing the persistent services and creating new CST-based HELICS federates. Using these APIs means having them installed in one or more appropriate places, depending on how the analysis is being developed.
3. Docker image - CST provides a docker image with the HELICS co-simulation platform and the CST API installed. This image may or may not be necessary or sufficient for a given analysis but can serve as a starting point for developing the use case.

Let's walk through the process of figuring out how to handle these components of CST for a given analysis


## Persistent Service Installation
The persistent services are services that will remain running all the time and are usable by any CST-based co-simulation. Generally, these are the services responsible for workflow management, metadata management, data collection and data presentation. The location of their installation will depend on the needs of that analysis. For smaller analysis with a single developer and analyst where the data collected is small to modest, installing these services locally is likely to work out fine. If the team is larger where multiple people will need to access the metadata or data or where the datasets may be larger than what your local machine can support, installing these services on a computer that the entire team can reach is likely to work out better. 

The good news is that all of the CST persistent services are stock installations of common servers so installing them should be straight-forward. 

### Local installation
If you decide to run the persistent services on your local machine, CST has scripting in place to launch the services.
1. Login to the PNNL registry 
   - `docker login -u COPPER_ACCESS_TOKEN -p z1kYDCJ-N2UChy54BG5s devops-registry.pnnl.gov`(TODO: Confirm this works on Windows)
   - The access token changes periodically and may need to be updated at ["Settings/Access Tokens"](https://devops.pnnl.gov/e-comp/thrust-3/copper/-/settings/access_tokens)
2. Pull down the CST Docker images
   - Linux and macOS: 
     - Clone in the CST repository at `https://devops.pnnl.gov/e-comp/thrust-3/copper.git`
       - You'll need an access token successfully pull this repository
       - Make sure you're in the "dev" or "main" branch and that it is up to date. The download script in the next step uses the Git commit to figure out which images to pull.
     - Use the `download_images.sh` shell script
     - **2025-03-26: Problem Trevor had** - This script did not work for me and I had to manually pull the images as outlined below. Additionally, because none of them had the "latest" tag I had to do the following: `sudo docker pull devops-registry.pnnl.gov/e-comp/thrust-3/copper/cosim-ubuntu:1.0.0-419f0a13` (manually iterating over all the images)
   - Windows (or if the `download_images.sh` script fails): Manually pull the images (TODO: confirm this works on Windows)
     - Use `docker pull` to pull the following images (_e.g._ `docker pull devops-registry.pnnl.gov/e-comp/thrust-3/copper/cosim-ubuntu:1.0.0`):
       - copper/cosim-build
       - copper/cosim-library
       - copper/cosim-python
       - copper/cosim-ubuntu
       - copper/cosim-helics
     - The `docker pull` command needs to be run in a command terminal; Docker Desktop provides one on all three platforms if needed. TODO add image showing this.
  
Once installed, the persistent services can be started:
1. **DEPRECATED: Now handled automatically in cosim.env.** Edit  "cosim.env" in the root of the repository, changing `$SIM_HOST` to the host name where the Docker containers were just installed 
   - Sometimes the hostname works, sometimes the IP works, sometimes either. It's always DNS.
2. Set up the local environment 
   - (Linux and macOS) run `source cosim.env` 
   - (Windows) TODO: figure out how to do this for Windows
3. Launch the persistent services
   - **2025-03-26: Problem Trevor had** - The images that were pulled from the Gitlab registry did not have the "latest" tag. They were versioned ("1.0.0-419f0a13"). I had to copy and re-tag the images doing `docker tag devops-registry.pnnl.gov/e-comp/thrust-3/copper/cosim-helics:1.0.0-419f0a13 cosim-cst:latest` (manually doing this for all the images).
   -  (Linux and macOS) Run "start_cu.sh" in the "scripts/stack" folder 
   -  (Windows) TODO: The "start_cu.sh" script might work in PowerShell; if not, we need a Windows-specific script

Finally, verify that the services are up and running.

1. Confirm the containers are running (and didn't crash immediately)
   - Docker Desktop shows the state of the containers
   - `docker ps` from the terminal does the same
2. TODO: Go to specific URLs for each of the services to confirm they are running.

### Remote installation
Probably the easiest way of installing the persistent services on a remote compute node is using Docker. Follow the instructions for setting up the persistent services using the links to the Docker registry pages for each of the packages is provided below.

- [Postgres](https://hub.docker.com/_/postgres/) (TODO: add version) - Time-series data logging
- [MongoDB](https://hub.docker.com/r/mongodb/mongodb-community-server) (TODO: add version) - Configuration database
- [Grafana](https://hub.docker.com/r/grafana/grafana) (TODO: add version) - Co-simulation monitoring (optional)



## API Installation
CST provides Python APIs for accessing the persistent services and creating new CST-based HELICS federates. These APIs are installed inside the CST Docker image but are also commonly installed outside the Docker image to allow for development of new tooling that isn't inside the CST Docker image.

To install the CST API outside the Docker image, clone the repository and use "pip" to install it.

1. Create a personal access token for the CST repository on PNNL's GitLab server
   1. "Edit profile" - "Access tokens"
   2. "Add new token" with the following permissions
     - "read_repository"
     - "write_repository"
     - "read_registry"
     - "write_registry"
2. `git clone https://devops.pnnl.gov/e-comp/thrust-3/copper.git` using the access token you just created as the password
3. Change your working directory to that of the root of the repository (where "setup.py" resides) and `pip install .`
4. Confirm installation with `pip list` to look for "cosim_toolbox" in the list of installed packages.


## Docker Image Installation
CST is built on top of HELICS, the technology that allows different simulation tools to exchange data during runtime. The CST image contains the HELICS co-simulation platform and the CST APIs and serves as the starting point for developing a new tool and/or a new Docker image specific to your analysis (this is further discussed on the ["Use Case Development"](./UseCaseDevelopment.md) page.)

**TODO**: Some portion of the "Local install" above needs to be done here?

### User Permissions
To allow code outside the Docker container to be run inside the docker container, permissions between the two need to be reconciled.

Whatever user you're logged in as needs to be a part of the `docker` group to use all images in CST.
- Linux and macOS
  1. `getent group docker` - If this returns nothing then add the group with `sudo groupadd docker`. 
  2. `sudo usermod -aG docker $USER` - Add the current user to the "docker" group
  3. `newgrp docker` - Logs into the new group. Alternatively, logging out and back in works as well.
  4. `docker run hello-world` - Confirm docker containers can be started buy running this test container.
- Windows
  1. TODO: Figure out what needs to be done on Windows