from datetime import datetime, timedelta
from textwrap import dedent
import random
import logging
from pathlib import Path as Path
from typing import Tuple
import os
import json

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG
# Operators; we need this to operate!
from airflow.operators.bash import BashOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.decorators import task
from airflow.utils.edgemodifier import Label

logger = logging.getLogger("airflow.task")

"""
Working outline of the copper airflow diagram.

To use: add "from copper_dags.copper import copper" to the top of a new dag python file (see test_capability_airflow_dag).
Important to note that airflow only recognizes DAGs defined at the top-level of files found somewhere within the dags directory.

Big to-dos and notes:
 - dags cannot access any files outside the dags folder (maybe because of setup in airflow docker?) Ex) a bash task cannot run env_cu.sh.
 - SubDags are deprecated (recommend TaskGroup instead)
"""
default_args = {
    'owner': 'airflow',
    'start_date': datetime(2022, 11, 12),
    'schedule': '@once'
}


def copper(run_name: str, federation_path: str, preprocessing_id: str, postprocessing_id: str):
    with DAG(dag_id=run_name, default_args=default_args, catchup=False) as dag:
        # # load in federation
        # with open(federation_path) as json_file:
        #     federation = json.load(json_file)
        federation = federation_path

        # -------------------------------------------------------
        #                   task definitions
        # -------------------------------------------------------
        @task(task_id="docker_federate")
        def docker_pull(federation: dict) -> Tuple[dict:[str, str], list:[str]]:
            """
            TODO: FILL IN
            Parse federation to pull out required docker images and federate names that belong to each image

            Args:
                federation (dict): federation json containing all federates
            """
            return {}, []

        federate_dict, docker_list = docker_pull(federation)

        docker_pull_tasks = []
        for docker_cont in docker_list:
            # TODO: FILL IN
            pull_task = BashOperator(bash_command=f"pull {docker_cont}")
            docker_pull_tasks.append(pull_task)

        @task(task_id="federate_metadata_load")
        def federate_metadata_load(federation: dict):
            """
            TODO: FILL IN
            load federate information into metadata database

            Args:
                federation (dict): federation json containing all federates
            """
            x = 10

        load_metadata = federate_metadata_load(federation)

        @task(task_id="configure_docker_container")
        def configure_docker_container(federate: str, docker_cont):
            """
            TODO: FILL IN
            For each docker container, configure the run command for a specific federate
            """
            x = 10

        @task(task_id="container_launch")
        def container_launch():
            """
            TODO: FILL IN
            Launch a docker container that will start a HELICS federate
            """
            x = 10

        preprocessing = TriggerDagRunOperator(trigger_dag_id=preprocessing_id)
        postprocessing = TriggerDagRunOperator(trigger_dag_id=postprocessing_id)

        cosim = []
        for federate in federate_dict:
            docker_configure = configure_docker_container(federate, federate_dict[federate])
            launch_fed = container_launch()
            docker_configure << launch_fed
            cosim.append(docker_configure)
            cosim.append(launch_fed)

        docker_pull_tasks + [load_metadata] << preprocessing
        preprocessing << cosim
        cosim << postprocessing
        return dag

# my_dag = copper("test_copper", "pth")
