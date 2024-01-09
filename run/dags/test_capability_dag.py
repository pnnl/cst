
from examples import capability_dag2

"""
Demonstrates how to pull in a DAG defined elsewhere and pass in variables
"""

my_airflow_dag = capability_dag2.capability_dag("capability_dag_4", '@once', "testing 2!")


def return_dag():
    return my_airflow_dag 
