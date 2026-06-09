from entsoe import EntsoePandasClient
import pandas as pd

class EntsoeRetrieval:

    def __init__(self, api_key, config_path):

        self.client = EntsoePandasClient(api_key=api_key)

    def _check_existing_dates(self, path):

        try:
            if 'pkl' in path:
                df = pd.read_pickle(path)
                df['datetime'] = pd.to_datetime(df['datetime'])
            elif 'csv' in path:
                df = pd.read_csv(path, parse_dates=['datetime'])
            else:
                raise ValueError("Unsupported file format. Use .pkl or .csv")
        except FileNotFoundError:
            return None, None

    def retrieve_generation(self, countries, start: pd.Timestamp, end: pd.Timestamp):
        
        for country in countries:
            df_country = self.client.query_load(country_code=country, start=start, end=end)
            df_country['country'] = country
            df_country.reset_index(names='datetime', inplace=True)
            # df_country['datetime'] = pd.to_datetime(df_country['datetime'])
            # df_country['datetime_utc'] = df_country['datetime'].dt.tz_convert('UTC')
            df = pd.concat([df, df_country], ignore_index=True)
        df.rename(columns={'Actual Load': 'load'}, inplace=True)

        return df
