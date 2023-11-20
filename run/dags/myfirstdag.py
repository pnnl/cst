
# To initiate the DAG Object
from airflow import DAG
# Importing datetime and timedelta modules for scheduling the DAGs
from datetime import timedelta, datetime
# Importing operators 
from airflow.operators.dummy_operator import DummyOperator

# Initiating the default_args
default_args = {
        'owner' : 'airflow',
        'start_date' : datetime(2022, 11, 12)
}

# Creating DAG Object
dag = DAG(dag_id='DAG-1',
        default_args=default_args,
        schedule_interval='@once', 
        catchup=False
    )
    

 # Creating first task
start = DummyOperator(task_id='start', dag=dag)

# Creating second task
end = DummyOperator(task_id='end', dag=dag)

start >> end