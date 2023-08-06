from airflow import DAG
from airflow.models import Variable
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.http.sensors.http import HttpSensor
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
import json
from datetime import datetime
import pandas as pd


def get_api_key():
    variable_key = 'WeatherAPIKey'
    exported_variable = Variable.get(variable_key)
    return exported_variable


API_KEY = get_api_key()
# for this city data will be featched
CITY = 'opole'


def _process_weather_data(ti):
    weather_data = ti.xcom_pull(task_ids='extract_weather_data')
    # getting value from the key then first element from list
    weather_description = weather_data["weather"][0]
    conditions = weather_description['main']
    conditions_description = weather_description['description']
    main_data = weather_data['main']
    temperature = main_data['temp']
    temperature_feels_like = main_data['feels_like']
    temperature_min = main_data['temp_min']
    temperature_max = main_data['temp_max']
    pressure = main_data['pressure']
    humidity = main_data['humidity']
    visibility = weather_data['visibility']
    wind_data = weather_data['wind']
    wind_speed = wind_data['speed']
    # extracing sunset and sunrise
    sunrise = weather_data['sys']['sunrise']
    sunset = weather_data['sys']['sunset']
    # adding value for timezone
    timezone = weather_data['timezone']
    sunrise += timezone
    sunset += timezone
    # converting unix timestamp to readable date
    sunset = datetime.fromtimestamp(sunset)
    sunrise = datetime.fromtimestamp(sunrise)
    data = {
        "conditions": conditions,
        "conditions_description": conditions_description,
        "temperature": temperature,
        "temperature_feels_like": temperature_feels_like,
        "temperature_min": temperature_min,
        "temperature_max": temperature_max,
        "pressure": pressure,
        "humidity": humidity,
        "visibility": visibility,
        "wind_speed": wind_speed,
        "sunrise": sunrise,
        "sunset": sunset
    }
    df = pd.DataFrame([data])
    temperature_columns = [
    "temperature", 
    "temperature_feels_like",
    "temperature_min", 
    "temperature_max"
    ]
    def _kelvin_to_celsius(kelvin):
        celsius = kelvin - 273.15
        return round(celsius, 2)
    df[temperature_columns] = df[temperature_columns].apply(_kelvin_to_celsius)
    df.to_csv(
        '/tmp/processed_data.csv',
        index=False,
        header=False
        )


def _store_data():
    hook = PostgresHook(postgres_conn_id='postgres')
    hook.copy_expert(
        sql="COPY weather_conditions FROM stdin WITH DELIMITER ',';",
        filename='/tmp/processed_data.csv'
    )


with DAG('weather_processing',
        start_date=datetime(2023,1,1),
        # run every 5 mins
        schedule_interval='*/10 * * * *',
        catchup=False
        ):

        create_table = PostgresOperator(
            task_id = 'create_table',
            postgres_conn_id = 'postgres',
            sql='''
            CREATE TABLE IF NOT EXISTS weather_conditions (
            conditions VARCHAR(255),
            conditions_description VARCHAR(255),
            temperature DECIMAL(10, 2),
            temperature_feels_like DECIMAL(10, 2),
            temperature_min DECIMAL(10, 2),
            temperature_max DECIMAL(10, 2),
            pressure INT,
            humidity INT,
            visibility INT,
            wind_speed DECIMAL(10, 2),
            sunrise TIMESTAMP,
            sunset TIMESTAMP
            );
            '''
        )

        is_api_available = HttpSensor(
        task_id = 'is_api_available',
        http_conn_id='weather_api',
        endpoint='data/2.5/weather',
        request_params={
            'q': CITY,
            'appid': API_KEY
        }
        )

        extract_weather_data = SimpleHttpOperator(
            task_id='extract_weather_data',
            http_conn_id='weather_api',
            endpoint='/data/2.5/weather',
            data={
            'q': CITY,
            'appid': API_KEY
            },
            method='GET',
            response_filter=lambda response: json.loads(response.text),
            log_response=True
        )

        process_weather_data = PythonOperator(
            task_id='process_weather_data',
            python_callable=_process_weather_data
        )

        store_data = PythonOperator(
            task_id='store_data',
            python_callable=_store_data
        )

        create_table >> is_api_available >> extract_weather_data >> process_weather_data >> store_data