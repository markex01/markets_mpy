import requests
import pandas as pd
from datetime import datetime, timedelta

class EsiosAPI:

    def __init__(self, key):

        self.key = key

        self.real_generation_dict = {
            10035: "Hidráulica total",
            1152: "Turbinación bombeo", 1153: "Nuclear", 
            1156: "Ciclo combinado",  10037: "Eólica", 
            1161: "Solar fotovoltaica", 1162: "Solar térmica",
            10039: "Cogeneración", 10036: "Carbón",
            10041: "Otras renovables",
            10040: "Residuos no renovables", 10062: "Residuos renovables", 1172: "Consumo bombeo",
            2167: "Entrega de batería", 2166: "Recarga de batería", 1173: "Enlace Baleares", 10048: "Saldo interconexiones"
            
            # 1150: "Hidraulica UGH", 1151: "Hidraulica  no UGH", 
            # 1152: "Turbinación bombeo", 1153: "Nuclear", 
            # 1156: "Ciclo combinado", 1157: "Fuel", 1158: "Gas Natural",  1159: "Eólica terrestre", 
            # 1160: "Eólica marina", 1161: "Solar fotovoltaica", 1162: "Solar térmica",
            # 1163: "Océano y geotérmica", 1164: "Gas Natural Cogeneración", 1165: "Derivados del petróleo ó carbón",
            # 1166: "Subproductos minería", 1167: "Energía residual", 1168: "Biomasa", 1169: "Biogás",
            # 1170: "Residuos domésticos y similares", 1171: "Residuos varios", 1172: "Consumo bombeo",
        }

        self.real_demand_dict = {
            1293:"Demanda real"
        }

        self.programmed_demmand_dict = {
            1292:"Demanda programada"
        }

        self.links_dict = {
            1174: "Importación Francia", 1175: "Importación Portugal",
            1176: "Importación Marruecos", 1177: "Importación Andorra", 1178: "Exportación Francia",
            1179: "Exportación Portugal", 1180: "Exportación Marruecos", 1181: "Exportación Andorra", 
        }

        self.type_dicts = {
            "real_generation": self.real_generation_dict,
            "real_demand": self.real_demand_dict,
            "links": self.links_dict,
        }



    def _get_raw_data(self, indicator: int, start_date:datetime, end_date: datetime):

        url = f'https://api.esios.ree.es/indicators/{indicator}?start_date={start_date}&end_date={end_date}&time_trunc=hour&time_agg=average'

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
            # print(df_response)
            df_response = pd.DataFrame(df_response.loc['values'].values[0])  

            if df_response.empty:
                return df_response        
            
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
            current_start = current_end + timedelta(hours=1)
        
        # Combine all chunks into a single DataFrame
        if chunk_dataframes:
            combined_df = pd.concat(chunk_dataframes, ignore_index=True)
            # Remove potential duplicates that might occur at chunk boundaries
            return combined_df.reset_index(drop=True)
        else:
            return pd.DataFrame()
        
    def get_data(self, type: str, start_date:datetime, end_date:datetime) -> pd.DataFrame:

        dict = self.type_dicts.get(type)

        if type == 'spot':
            df_response = self._get_chunks(indicator=600, start_date=start_date, end_date=end_date)
            return df_response
        
        if dict is None:
            raise ValueError(f"Type '{type}' not recognized. Available types: {list(self.type_dicts.keys())}")

        # We take spanish spot prices as the base dataframe, as for some indicators there are no values for all hours
        df_response = self._get_chunks(indicator=600, start_date=start_date, end_date=end_date)
        df_response = df_response[df_response['geo_id'] == 3]
        df_response = df_response.rename(columns={'value': "spot_price"})
        df_response = df_response[['datetime', 'spot_price']]
        df_response['dup'] = df_response.groupby(['datetime']).cumcount()

        for indicator, name in dict.items():
            df = self._get_chunks(indicator=indicator, start_date=start_date, end_date=end_date)
            if not df.empty:
                df = df.rename(columns={indicator: name})
                df['dup'] = df.groupby(['datetime', 'geo_id']).cumcount()
                df = df.rename(columns={'value':indicator})
                df = df[['datetime', 'dup', 'geo_id', indicator]]
                df = df.groupby(['datetime', 'dup'])[indicator].sum().reset_index()
                df = df.rename(columns={indicator: name})
                df_response = pd.merge(df_response, df, on=['datetime', 'dup'], how='left')
                
            else:
                print(f"No data retrieved for indicator {indicator} ({name})")
        
        df_response.drop(columns=['spot_price', 'dup'], inplace=True)

        return df_response



