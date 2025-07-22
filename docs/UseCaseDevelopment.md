# Developing a Use Case with CoSim Toolbox

## Building a Use Case Specific Image
Though the base CST Docker image does not contain much, it does contain the two key pieces of software needed to develop a new use case: HELICS and the CST API. If possible, extending the CST Docker image is the best way to create a comprehensive and distributable method of installing the necessary software and running a specific use case. Assuming all of the required software can be run on Linux, the general process is to spin up a container of the base CST image, install the use case specific software inside said container, and then save off that container as a new image.


### Accessing the Host Environment
CST's runnner scripts generally take care of linking the Docker container to the host environment through opening ports and creating mount points. A means of doing this in a development environment needs to be developed to make it easy to do the same thing when developing.

### Extending the CST Image to Make a Development Container

First thing, make a .dockerfile with all the existing tools you need that will be built on top of the core CST image. This could also include cloning in any repositories that may be used during development. Alternatively, the use case developer can start running a Docker container and enter it interactively, install whatever needs to be installed, and then commit out the running container as a new image. One developer needs to do this once and then distribute the new image as the starting point for whoever else is helping out with use case development

If a .dockerfile is made, that should be under version control so that the image can be remade in the future.

As along as the changes in the use case development are being captured in a location under version control, those changes can be distributed and managed just like in any other repository. 

Changes made in the development environment itself (to the container) need to be managed in some other way. These changes might be creating new mount points, opening specific ports.


## Using IDEs to Access the Development Container

VS Code and PyCharm CE both have capabilities that allow development inside a container environment. This provides a way to write and debug new tools and capabilities in the Docker container where they will be running with the conveniences of an IDE (like interactive debugging). 

### Local development

Docker must be installed locally and the image you wish to run and enter must be locally installed.

#### VS Code

VS Code provides an extension to make it easy to access a local container in a manner similar to connecting to a remote server. To access this capability in VS Code install the Docker extension and when it runs, it will find any local Docker images. Right-clicking on any image provides the option to "Start" and then "Attach Visual Studio Code". This then presents a VS Code Window inside the container where development can proceed.

#### PyCharm CE

TODO

### Remote Development

Log into the remote server outside the IDE. This server needs to have Docker installed and a copy of the Docker image being used.

Launch the IDE on the remote server with the display set to forward to your local machine.

Within the IDE, launch the Docker container.

TODO: does this give you the ability to debug code within the container? I don't think it would.


