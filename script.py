import requests
import os
import csv
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime
import time
import snowflake.connector

POLYGON_API_KEY = os.getenv('POLYGON_API_KEY')

LIMIT = 500

DS = '2025-09-27'

def run_stock_job():
    DS = datetime.now().strftime('%Y-%m-%d')
    url = f'https://api.polygon.io/v3/reference/tickers?market=stocks&active=true&order=asc&limit={LIMIT}&sort=ticker&apiKey={POLYGON_API_KEY}'
    response = requests.get(url)
    tickers = []

    data = response.json()
    for ticker in data['results']:
        ticker['ds'] = DS
        tickers.append(ticker)

    while 'next_url' in data:
        print('requesting next page', data['next_url'])
        response = requests.get(data['next_url'] + f'&apiKey={POLYGON_API_KEY}')
        data = response.json()

        print(data)

        for ticker in data['results']:
            ticker['ds'] = DS
            tickers.append(ticker)
        time.sleep(12)

    example_ticker = {
                    'ticker': 'BBAG', 
                    'name': 'JPMorgan BetaBuilders U.S. Aggregate Bond ETF', 
                    'market': 'stocks', 
                    'locale': 'us', 
                    'primary_exchange': 'ARCX', 
                    'type': 'ETF', 
                    'active': True, 
                    'currency_name': 'usd', 
                    'cik': '0001485894', 
                    'composite_figi': 'BBG00MSHTGF0', 
                    'share_class_figi': 'BBG00MSHTH59', 
                    'last_updated_utc': '2025-09-16T06:05:51.696762333Z',
                    'ds': '2025-09-27'
                    }

    fieldnames = list(example_ticker.keys())

    #Loading to Snowflake instead of loading to CSV
    load_to_snowflake(tickers, fieldnames)
    print(f'Loaded {len(tickers)} rows to Snowflake')


'''
    output_csv = 'tickers.csv'
    with open(output_csv, mode = 'w', newline = '', encoding = 'utf-8') as f:
        writer = csv.DictWriter(f, fieldnames = fieldnames)
        writer.writeheader()
        for t in tickers:
            row = {key: t.get(key, '') for key in fieldnames}
            writer.writerow(row)
    print(f'Wrote {len(tickers)} rows to {output_csv}')
'''


def load_to_snowflake(rows, fieldnames):
    connect_kwargs = {
        'user': os.getenv('SNOWFLAKE_USER'),
        'password': os.getenv('SNOWFLAKE_PASSWORD'),
    }

    account = os.getenv('SNOWFLAKE_ACCOUNT')
    if account:
        connect_kwargs['account'] = account 

    warehouse = os.getenv('SNOWFLAKE_WAREHOUSE')
    database = os.getenv('SNOWFLAKE_DATABASE')
    schema = os.getenv('SNOWFLAKE_SCHEMA')      
    role = os.getenv('SNOWFLAKE_ROLE')

    if warehouse: 
        connect_kwargs['warehouse'] = warehouse

    if database:
        connect_kwargs['database'] = database

    if schema:
        connect_kwargs['schema'] = schema
    
    if role:
        connect_kwargs['role'] = role 

    print(connect_kwargs)

    conn = snowflake.connector.connect(
        user = connect_kwargs['user'],
        password = connect_kwargs['password'],
        account = connect_kwargs['account'],
        database = connect_kwargs['database'],
        schema = connect_kwargs['schema'],
        role = connect_kwargs['role'],
        session_parameters = {
            'CLIENT_TELEMETRY': False
        }
    )

    try: 
        cs = conn.cursor()
        try: 
            table_name = os.getenv('SNOWFLAKE_TABLE', 'stock_tickers')
            
            #Defining the typed schemas based on the example_ticker
            type_overrides = {
                'ticker': 'VARCHAR',
                'name': 'VARCHAR',
                'market': 'VARCHAR',
                'locale': 'VARCHAR',
                'primary_exchange': 'VARCHAR',
                'type': 'VARCHAR',
                'active': 'BOOLEAN',
                'currency_name': 'VARCHAR',
                'cik': 'VARCHAR',
                'composite_figi': 'VARCHAR',
                'share_class_figi': 'VARCHAR',
                'last_updated_utc': 'TIMESTAMP_NTZ',
                'ds': 'VARCHAR'
            }

            columns_sql_parts = []
            for col in fieldnames:
                col_type = type_overrides.get(col, 'VARCHAR')
                columns_sql_parts.append(f' {col.upper()} {col_type}')

            create_table_sql = f'CREATE TABLE IF NOT EXISTS {table_name} ( ' + ', '.join(columns_sql_parts) + ')'
            cs.execute(create_table_sql)

            column_list = ', '.join([c.upper() for c in fieldnames])
            placeholders = ', '.join(['%s' for _ in fieldnames])
            insert_sql = f'INSERT INTO {table_name} ( {column_list} ) VALUES ( {placeholders} )'

            transformed = []

            for t in rows:
                row = tuple(t.get(k, None) for k in fieldnames)
                print(row)
                transformed.append(row)

            if transformed:
                cs.executemany(insert_sql, transformed)
        finally:
            cs.close()
    finally:
        conn.close()

if __name__ == '__main__':
    run_stock_job() 