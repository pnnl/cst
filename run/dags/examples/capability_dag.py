
from datetime import datetime, timedelta
from textwrap import dedent
import random
import logging
import os
from pathlib import Path as Path

# Operators; we need this to operate!
from airflow.decorators import task, dag
from airflow.operators.bash import BashOperator
from airflow.operators.python import BranchPythonOperator
from airflow.utils.edgemodifier import Label
logger = logging.getLogger("airflow.task")


default_args = {
        'owner' : 'airflow',
        'start_date' : datetime(2022, 11, 12)
}

def successful_dag(context):
    logger.info(f"DAG has succeeded, run_id: {context['run_id']}")

    
def log_info(context):
    for key in context:
        logger.warning(f"key = {key}, value = {context[key]}")
    

@dag(dag_id="addition_dag",
     default_args=default_args,
     catchup=False,
     schedule_interval='@once',
     on_success_callback=[log_info])
def addition_dag():
    """
    Example DAG that performs addition or subtraction on randomly generated numbers.
    
    Includes python functions as tasks, bash scripts as tasks, conditional logic,
    changing parameters, chain of tasks on failure, chain of tasks on success.
    """
    
    
    # -------------------------------------------------------
    #                   task definitions
    # -------------------------------------------------------
    bash_task = BashOperator(
        task_id="bash_task",
        bash_command="pwd",
        cwd= '/opt/example'
    )
    
    # join task at completion
    @task(task_id = "join_success", trigger_rule="none_failed_min_one_success", on_success_callback=successful_dag)
    def join():
        logger.warning(f"{os.listdir('/opt/example')}\n")
        logger.info("Successfully ran DAG")
    
    @task(task_id = "join_failure", trigger_rule="one_failed", on_success_callback=successful_dag)
    def join_failure():
        logger.info("Failed DAG run")

    # test python functions and create instances of tasks
    @task(task_id="python_add")
    def add_task(inp1:int, inp2:int):
        logger.info(f"Addition result: {inp1 + inp2}")
        return inp1 + inp2

    @task(task_id="python_subtract")
    def subtract_task(inp1:int, inp2:int):
        if inp1 - inp2 < 0:
            logger.error(f"negative value: {inp1 - inp2}")
            raise Exception("Negative value occured!")
        logger.info(f"Subtraction result: {inp1 - inp2}")
        return inp1 - inp2


    @task(task_id = "generate_numbers")
    def generate_num(is_random):
        logger.warning(f"is_randomw = {is_random}, type = {type(is_random)}")
        if is_random:
            logger.info("randomly generating number")
            return random.randint(1,10)
        logger.info("choosing 4")
        return 4

    # test conditional task execution
    def add_or_subtract():
        i = random.randint(1,10)
        if i % 2 == 0:
            return "python_add"
        else:
            return "python_subtract"
        
    # -------------------------------------------------------
    #                  create task objects
    # -------------------------------------------------------
    join_task = join()
    join_failure_task = join_failure()
    generate_num_1 = generate_num(False)
    generate_num_2 = generate_num(False)
    addition = add_task(generate_num_1, generate_num_2)
    subtraction = subtract_task(generate_num_1, generate_num_2)
    branch_task = BranchPythonOperator(
        task_id="branch_task",
        python_callable=add_or_subtract
    )
    
    # -------------------------------------------------------
    #               establish task dependencies
    # -------------------------------------------------------
    # bash_task >> branch_task
    branch_task >> Label("addition") >> addition
    branch_task >> Label("subtraction") >> subtraction
    addition >> [join_task, join_failure_task]
    subtraction >> [join_task, join_failure_task]
    

my_dag = addition_dag()

