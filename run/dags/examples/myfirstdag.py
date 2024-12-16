import os
import sys
# Importing datetime and timedelta modules for scheduling the DAGs
from datetime import datetime
# Importing operators
from airflow.operators.python import PythonOperator
from airflow.contrib.hooks.ssh_hook import SSHHook
# To initiate the DAG Object
from airflow import DAG
# Import cosim toolbox
from cosim_toolbox.dockerRunner import DockerRunner

# Add new code
sys.path.insert(0, '/python_extended/test_federation')
import runner as myr


def prepare_case():
    _scenario_name = "test_Scenario"
    _schema_name = "test_Schema"
    _federation_name = "test_Federation"
    r = myr.Runner(_scenario_name, _schema_name, _federation_name, True)
    r.define_scenario()


def prepare_yaml():
    _scenario_name = "test_Scenario"
    os.chdir("/python_extended/test_federation")
    DockerRunner.define_yaml(_scenario_name)


def run_yaml():
    cosim = os.environ.get("SIM_DIR", "/home/worker/copper")
    _scenario_name = "test_Scenario"
    ssh = SSHHook(ssh_conn_id='myssh')
    ssh_client = None
    try:
        ssh_client = ssh.get_conn()
        ssh_client.load_system_host_keys()
        channel = ssh_client.invoke_shell()
        stdin = channel.makefile('wb')
        stdout = channel.makefile('rb')
        stdin.write('''
cd ''' + cosim + '''/run/python/test_federation || exit
docker compose -f ''' + _scenario_name + '''.yaml up
docker compose -f ''' + _scenario_name + '''.yaml down
exit
        ''')
        print(stdout.read())
        stdout.close()
        stdin.close()

    finally:
        if ssh_client:
            ssh_client.close()


# Initiating the default_args
default_args = {
        'owner': 'airflow',
        'start_date': datetime(2022, 11, 12)
}

# Creating DAG Object
dag = DAG(dag_id='DAG-1',
          default_args=default_args,
          schedule_interval='@once',
          catchup=False
          )

task_a = PythonOperator(
    dag=dag,    
    task_id='prepare_federation_case',
    python_callable=prepare_case
)

task_b = PythonOperator(
    dag=dag,    
    task_id='prepare_compose_file',
    python_callable=prepare_yaml
)

task_c = PythonOperator(
    dag=dag,
    task_id='run_compose_file',
    python_callable=run_yaml
)

task_a >> task_b >> task_c
