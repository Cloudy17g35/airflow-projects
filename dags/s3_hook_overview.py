import os
from datetime import datetime
from airflow.models import DAG
from airflow.operators.python import PythonOperator
from airflow.hooks.S3_hook import S3Hook

TEST_BUCKET = 'test-ksawery-s3-bucket'


def create_file():
    with open('test.txt', 'w') as f:
        f.write('hello world')


def upload_to_s3() -> None:
    hook = S3Hook('aws_conn')
    hook.load_file(
        filename='test.txt',
        key='some_key/test.txt',
        bucket_name=TEST_BUCKET,
        replace=True
    )


def check_if_key_exists():
    hook = S3Hook('aws_conn')
    result = hook.check_for_key(
        bucket_name='test-ksawery-s3-bucket',
        key='some_key/test.txt'
    )

    if result is False:
        raise ValueError('File not found')


def download_from_s3() -> None:
    hook = S3Hook('aws_conn')
    file_name = hook.download_file(
        key='some_key/test.txt',
        bucket_name=TEST_BUCKET
    )
    # will return absolute path
    return file_name


def rename_file(ti, new_name: str):
    list_of_args = ti.xcom_pull(task_ids=['download_from_s3'])
    # need to extract first element from xcom
    # since it looks like that ['/tmp/***_tmp_0xnf56ew']
    downloaded_file_name = list_of_args[0]
    # to extract the dirs in which file exists
    downloaded_file_path = '/'.join(downloaded_file_name.split('/')[:-1])
    new_name_for_file = f'{downloaded_file_path}/{new_name}'
    os.rename(src=downloaded_file_name, dst=new_name_for_file)


with DAG(
    dag_id='s3_hook_overview',
    schedule_interval='@daily',
    start_date=datetime(2023, 9, 1),
    catchup=False
) as dag:

    task_create_file = PythonOperator(
        task_id='create_file',
        python_callable=create_file
    )

    task_upload_to_s3 = PythonOperator(
        task_id='upload_to_s3',
        python_callable=upload_to_s3
    )

    task_check_if_key_exists = PythonOperator(
        task_id='check_if_key_exists',
        python_callable=check_if_key_exists
    )

    task_download_from_s3 = PythonOperator(
        task_id='download_from_s3',
        python_callable=download_from_s3
    )

    task_rename_file = PythonOperator(
        task_id='rename_file',
        python_callable=rename_file,
        op_kwargs={'new_name': 'file_downloaded_from_s3.txt'}
    )

    task_create_file >> task_upload_to_s3 \
    >> task_check_if_key_exists \
    >> task_download_from_s3 >> task_rename_file
