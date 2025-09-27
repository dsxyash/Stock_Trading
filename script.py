import requests
import os
import csv
from dotenv import load_dotenv
load_dotenv()
import time

POLYGON_API_KEY = os.getenv('POLYGON_API_KEY')

LIMIT = 500

print(POLYGON_API_KEY)


def run_stock_job():
    url = f'https://api.polygon.io/v3/reference/tickers?market=stocks&active=true&order=asc&limit={LIMIT}&sort=ticker&apiKey={POLYGON_API_KEY}'
    response = requests.get(url)
    tickers = []


    data = response.json()
    for ticker in data['results']:
        tickers.append(ticker)

    while 'next_url' in data:
        print('requesting next page', data['next_url'])
        response = requests.get(data['next_url'] + f'&apiKey={POLYGON_API_KEY}')
        data = response.json()

        print(data)
        for ticker in data['results']:
            tickers.append(ticker)
        time.sleep(12)

    example_ticker = {'ticker': 'BBAG', 
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
                    'last_updated_utc': '2025-09-16T06:05:51.696762333Z'}

    fieldnames = list(example_ticker.keys())
    output_csv = 'tickers.csv'
    with open(output_csv, mode = 'w', newline = '', encoding = 'utf-8') as f:
        writer = csv.DictWriter(f, fieldnames = fieldnames)
        writer.writeheader()
        for t in tickers:
            row = {key: t.get(key, '') for key in fieldnames}
            writer.writerow(row)
    print(f'Wrote {len(tickers)} rows to {output_csv}')


if __name__ == '__ main__':
    run_stock_job() 