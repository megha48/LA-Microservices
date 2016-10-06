from airflow import DAG
from airflow.operators import PythonOperator, BranchPythonOperator, BashOperator
from upload_file import *
from process_checklist import *
import datetime

pipeline_args = {
	'owner':'megha',
	'start_date':datetime(2016, 10, 04)-timedelta(days=1)
}

path_personal_info = '/Users/megha/Documents/FOS/CustomerPersonal.xlsx'
path_checklist = '/Users/megha/Documents/FOS/ChecklistDocuments.xlsx'

def process_sheets():
	r_checklist =read_checklist_sheet(path_checklist)
	[vals, db_map_values] = read_basic_info_sheet(path_personal_info)


los_dag = DAG('los_docs', default_args=pipeline_args, schedule_interval='@once')

# task instantiation
t0 = BashOperator(
	task_id = 'start',
	bash_command = 'echo "Task for Uploading Documents Started" ',
	dag = ml_dag
	)
t1 = PythonOperator(
	task_id =  'read_sheets',
	python_callable = ,
	dag = ml_dag
	)

t2 = PythonOperator(
	task_id =  'sub_sampler',
	python_callable = subsample_for_sample_selection,
	dag = ml_dag
	)

t3 = PythonOperator(
 	task_id =  'ml_algo',
 	python_callable = active_learning_iterations,
 	dag = ml_dag
 	)
