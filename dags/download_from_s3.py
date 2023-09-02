import os
from datetime import datetime
from airflow.models import DAG
from airflow.operators.python import PythonOperator
from airflow.hooks.S3_hook import S3Hook


def download_from_s3(key:str, bucket_name:str) -> None:
    hook = S3Hook('aws_conn')
    file_name = hook.download_file(key=key,bucket_name=bucket_name)
    # will return absolute path
    return file_name


def rename_file(ti, new_name:str):
    download_file_name = ti.xcom_pull(task_ids=['download_from_s3'])
    print(download_file_name)
    downloaded_file_path = '/'.join(download_file_name[0].split('/')[:-1])
    os.rename(src=download_file_name[0], dst=f'{downloaded_file_path}/{new_name}')


with DAG(
    dag_id='s3_dag_download',
    schedule_interval='@daily',
    start_date=datetime(2023,9,1),
    catchup=False) as dag:
    

    task_download_from_s3 = PythonOperator(
        task_id='download_from_s3',
        python_callable=download_from_s3,
        op_kwargs={
            'key': 'test.txt',
            'bucket_name': 'ksawery-test-bucket'
        }
    )

    task_rename_file = PythonOperator(
        task_id='rename_file',
        python_callable=rename_file,
        op_kwargs={'new_name': 'file_downloaded_from_s3.txt'}
    )

    task_download_from_s3 >> task_rename_file