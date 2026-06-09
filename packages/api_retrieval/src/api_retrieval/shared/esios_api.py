import requests
import pandas as pd
from datetime import datetime, timedelta

class EsiosAPI:

    def __init__(self, key, df_prices):

        self.key = key

    def _get_raw_data(self, indicator: int, start_date:datetime, end_date: datetime):

        url = f'https://api.esios.ree.es/indicators/{indicator}?start_date={start_date}&end_date={end_date}&time_trunc=hour&geo_ids[]=3' #&time_agg=average

        headers = {
            "Content-type": "application/json",
            "Accept": "application/json; application/vnd.esios-api-v1+json",
            "x-api-key": self.key,
            #"Host": "api.esios.ree.es",
            #"Cookie": ""
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            df_response = pd.DataFrame(response.json())        
            df_response = pd.DataFrame(df_response.loc['values'].values[0])  
            df_response = df_response[['datetime', 'value']]
            df_response['datetime'] = df_response['datetime'].apply(lambda x: x[:-7])
            df_response['datetime'] = pd.to_datetime(df_response['datetime'])
            return df_response
        else:
            df_response = pd.DataFrame()
            print(f"Error {response.status_code}: {response.text}")
            return df_response
        
    def _get_chunks(self, indicator: int, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Retrieve API data in 30-day chunks and combine into a single DataFrame.
        
        Args:
            indicator: The indicator ID for the ESIOS API
            start_date: Start date for data retrieval
            end_date: End date for data retrieval
        
        Returns:
            Combined DataFrame with all data from chunks
        """
        if start_date >= end_date:
            raise ValueError("start_date must be earlier than end_date")
        
        chunk_dataframes = []
        current_start = start_date
        chunk_size = timedelta(days=30)
        
        while current_start < end_date:
            # Calculate end date for this chunk
            current_end = min(current_start + chunk_size, end_date)
            
            print(f"Retrieving data for {indicator} from {current_start.date()} to {current_end.date()}")
            
            # Get data for this chunk
            chunk_df = self._get_raw_data(indicator, current_start, current_end)
            
            # Only add non-empty DataFrames
            if not chunk_df.empty:
                chunk_dataframes.append(chunk_df)
            
            # Move to next chunk
            current_start = current_end
        
        # Combine all chunks into a single DataFrame
        if chunk_dataframes:
            combined_df = pd.concat(chunk_dataframes, ignore_index=True)
            # Remove potential duplicates that might occur at chunk boundaries
            combined_df = combined_df.drop_duplicates(subset=['datetime']).sort_values('datetime')
            return combined_df.reset_index(drop=True)
        else:
            return pd.DataFrame(columns=['datetime', 'value'])
