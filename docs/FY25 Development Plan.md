# FY25 Development Plan 

FY25 is the last year of funding for the CoSim Toolbox project. (A supplemental project or projects may be proposed in FY26 and/or FY27 but the funding level will likely be considerably smaller.) Given that, it is essential that CoSim Toolbox reach a useable state by the end of FY25 as this is the last guaranteed traunch of funding we have to get it into a useable state.

The development plan as presented to E-COMP leadership is provided below:

The FY24 efforts for E-COMP produced CoSim Toolbox (CST), an integrated suite of tools designed to facilitate faster development of multi-entity co-simulations through the use of a HELICS federate class (serving as a template for those needing to integrate a new tool into CST), configuration management APIs, data collection APIs, and a workflow management tool. Additionally, significant effort has been put into implementing continuous development tooling to allow increase the quality and maintainability of the code. In FY25, there are two critical tasks and three supplemental tasks that while not mission critical, will enhance the usability of CST. The critical tasks are (1) developing robust user documentation for the tool, (2) supporting the running of selected use cases for FY25 on CST which may include adding support for new analysis tools required by the use case. Additional optional enhancements include (1) co-simulation construction tooling, which would increase the user-friendliness of the tool particularly for running large and complex models, (2) further exploration of workflow tools, and (3) testing the code for robustness and scalability.
 
**Milestones:**
- Completion of evaluation of workflow tools – March 31, 2025
- Completion of scalability testing – June 30, 2025
- Complete documentation of CST – Sept 1, 2025
 
**Deliverables:**
- Documentation of evaluation of workflow tools – March 31, 2025
- Documentation of scalability testing – June 30, 2025
- Completed documentation on locally hosted ReadTheDocs - Sept 1, 2025

# Planned activities

## Use Case Support - $50k ~ 325 hours

At this time, it is likely that the FY24 Off-Shore Wing (OSW) use case will be the focus of the efforts in FY25 as well with some effort being put into the RECOOP (Olympic Peninsula microgrdi) use case late in FY25. We don't know the level of support that will be required but we are hoping to minimize this effort.

## Workflow Tool Evaulation - $25k ~ 150 hours

Thus far, the ambition of supporting one or more workflow tools in CoSim Toolbox has not been realized. Though Airflow is included in our persistent services Docker stack, it is not currently being used though some experimentation and evaluation was conducted early in FY24. Similarly, a Jupyter-based workflow was also investigated early in FY24 but has not received much attention since then. The question of what, if any workflow tool(s) we should use be supporting in CoSim Toolbox needs to be resolved early in FY25. This is likely to be challenging given the low user count we have experienced to date and we don't anticipate this changing quickly. Given that, we will have to decide as a team what we think the best way for a user to execute a known analysis workflow (pre-processing/set-up, simulation, post-processing).

## Scalability Testing - $50k ~ 325 hours

At this time, overhead produced by using CoSim Toolbox is undefined. On non-Linux platforms Docker must run a virtual machine to host the docker engine and this is known to produce some additional computational costs. Additionally, the federate.py class has been designed for ease of use over performance and it is unknown what, if any, computational costs this will produce. 

As part of evaluating the software architecture of CoSim Toolbox, scalability testing will be undertaken. This testing will use both federates based on CoSim Toolbox's federate.py as well as third party tools anticipated to be used by CoSim Toolbox users such as GridLAB-D.

## New Feature Development - $50k ~ 325 hours

CoSim Toolbox is far from feature complete and there are a number of features currently in the backlog that would provide significant value to CoSim Toolbox users. Candidate features include co-simulation profiling, centralized logging in the time-series database, and interactive debugging. The development team will evaulate the backlog, adding additional items as necessary, creating a parento list, and developing them as budget allows.

## Documenation - $50k ~ 325 hours

To enable CoSim Toolbox users to actually use the software without direct developer support, high quality and useful documenation needs to be written and implemented. This includes not only documents describing how to install and use CoSim Toolbox but also examples users users can run to provide live demonstrations of the use of the CoSim Toolbox APIs and configuration conventions but also to use as a starting point.

## DevOps Improvements - $50k ~ 325 hours

For CoSim Toolbox to be successful, it is essential that the software be developed with sufficient quality and have appropriate supporting infrastructure in place to maintain its quality. This often goes by the name "DevOps" and includes things like definition and enforcement of a coding style guide, automated testing, automated artifact construction (_e.g._ Docker images) among other things. Some of these items exist now in some form and some need further development.

## Admin and Outreach - $25k ~ 150 hours

In addition to the traditional management tasks, there will be some effort put into publicity around CoSim Toolbox and finding institutions that are willing to license it. Some initial effort has been made in FY24 and a small list of candidate institutions has been formed. 

# Scoping for FY26 and FY27 activities

Given the limited budget to accomplish the above tasks, it will be important to evaulate effort and importance of any of the above tasks and be willing to cut them from the scope in FY25. Particuarly those tasks that are cleanly separable and distinct from the core development of CoSim Toolbox are the best candidates to be removed by FY25 scope with the intention of proposing them as distinct activities in FY26 and/or FY27. The budget expected for these tasks should be expected to be modest and this strategy should not be used as blind wish fulfillment ("Let's just plan on tackling that in FY26 and assume we'll get sufficient budget to do so.")