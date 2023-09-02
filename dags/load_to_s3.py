from datetime import datetime
from airflow.models import DAG
from airflow.operators.python import PythonOperator
from airflow.hooks.S3_hook import S3Hook


def create_file():
    with open('test.txt', 'w') as f:
        f.write('hello world')


def upload_to_s3(filename:str, key:str, bucket_name:str) -> None:
    hook = S3Hook('aws_conn')
    hook.load_file(filename=filename, key=key, bucket_name=bucket_name, replace=True)


with DAG(
    dag_id='s3_dag_load',
    schedule_interval='@daily',
    start_date=datetime(2023,9,1),
    catchup=False) as dag:


    task_create_file = PythonOperator(
        task_id = 'create_file',
        python_callable=create_file
    )

    task_upload_to_s3 = PythonOperator(
        task_id='upload_to_s3',
        python_callable=upload_to_s3,
        op_kwargs={
            'filename': 'test.txt',
            'key': 'test.txt',
            'bucket_name': 'ksawery-test-bucket'
    }
    )

    task_create_file >> task_upload_to_s3