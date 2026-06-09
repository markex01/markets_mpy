import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import timedelta
import time
from entsoe import EntsoePandasClient
from entsoe.exceptions import NoMatchingDataError


# -----------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------
# CAPTURE PRICE DOWNLOAD
# -----------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------


def fetch_generation_by_tech(zone_code, psr_type, tech_name,full_index,start, end):
    chunk_size = timedelta(days=90)
    current = start
    chunks = []
    # ENTSOE API client
    api_key = '7b788dda-a91f-4a20-9a64-aee81de70012'
    client = EntsoePandasClient(api_key=api_key)

    while current < end:
        chunk_end = min(current + chunk_size, end)
        for attempt in range(5):
            try:
                print(f"Fetching {tech_name} from {current} to {chunk_end}...")
                df = client.query_generation(zone_code, start=current, end=chunk_end, psr_type=psr_type)
                chunks.append(df)
                break
            except NoMatchingDataError:
                print(f"No data for {tech_name} from {current} to {chunk_end}")
                break
            except Exception as e:
                if attempt == 4:
                    print(f"Failed chunk {current} to {chunk_end}: {e}")
                    break
                wait = 2 ** attempt
                print(f"Retry {current} to {chunk_end} in {wait} sec: {e}")
                time.sleep(wait)
        current = chunk_end

    if chunks:
        df_all = pd.concat(chunks).resample('h').mean().reindex(full_index)

        # Convert to one-column DataFrame named tech_name
        if isinstance(df_all, pd.Series):
            return df_all.to_frame(name=tech_name)
        elif isinstance(df_all, pd.DataFrame):
            # If it's multi-column, sum them
            return pd.DataFrame({tech_name: df_all.sum(axis=1)})
    else:
        return pd.DataFrame(index=full_index)
    


# Descarga de producción por país y tecnología
def download_generation_all(zones, techs, full_index,start_dict, end_dict):
    generation_data = {}

    for country, zone_code in zones.items():
        print(f"\n Descargando generación para {country}")
        df_country = pd.DataFrame(index=full_index[country])

        for tech_name, psr_type in techs.items():
            df_tech = fetch_generation_by_tech(zone_code, psr_type,tech_name, full_index[country],start_dict[country], end_dict[country])
            if not df_tech.empty:
                df_country[tech_name] = df_tech[tech_name]

        generation_data[country] = df_country

    return generation_data


# Función para obtener precios por chunks con reintentos
def fetch_prices(zone_code, start, end, full_index):
    # ENTSOE API client
    api_key = '7b788dda-a91f-4a20-9a64-aee81de70012'
    client = EntsoePandasClient(api_key=api_key)

    chunk_size = timedelta(days=90)
    current = start
    chunks = []

    while current < end:
        chunk_end = min(current + chunk_size, end)
        for attempt in range(5):
            try:
                print(f"Fetching prices {current} to {chunk_end}...")
                df = client.query_day_ahead_prices(zone_code, start=current, end=chunk_end)
                chunks.append(df)
                break
            except Exception as e:
                if attempt == 4:
                    print(f"Failed chunk {current} to {chunk_end}: {e}")
                    break
                wait = 2 ** attempt
                print(f"Retrying in {wait} sec for {current} to {chunk_end}: {e}")
                time.sleep(wait)
        current = chunk_end

    if chunks:
        df_all = pd.concat(chunks).resample('h').mean().reindex(full_index)
        df_all.name = 'Price'
        return df_all.to_frame()
    else:
        print("No price data retrieved.")
        return pd.DataFrame(index=full_index)


def calculate_monthly_capture_prices(price_data, generation_data):
    capture_results = {}

    for country in price_data:
        print(f"\n Calculando precios capturados para {country}")
        prices_df = price_data[country].copy()
        gen_df = generation_data[country].copy()

        combined = prices_df.join(gen_df, how='inner')
        monthly = combined.resample('ME').agg({'Price': 'mean'})

        for tech in gen_df.columns:
            if country == 'Ireland' and tech == 'Solar':
                continue
            # Suma de generación por mes
            gen_sum = combined.resample('ME')[tech].sum()
            # Precio capturado mensual
            cap_price = combined.resample('ME').apply(
                lambda x: (x['Price'] * x[tech]).sum() / x[tech].sum() if x[tech].sum() != 0 else None
            )
            monthly[f'{tech} Generation'] = gen_sum
            monthly[f'{tech} Capture Price'] = cap_price
            monthly[f'{tech} Capture %'] = cap_price / monthly['Price']

        capture_results[country] = monthly

    return capture_results

def calculate_yearly_capture_prices(price_data: dict, generation_data: dict) -> dict:
    
    capture_results = {}

    for country in price_data:
        print(f"\nCalculando precios capturados anuales para {country}")
        prices_df = price_data[country].copy()
        gen_df = generation_data[country].copy()

        # Combinar precios y generación
        combined = prices_df.join(gen_df, how='inner')
        yearly = combined.resample('YE').agg({'Price': 'mean'})

        for tech in gen_df.columns:
            if country == 'Ireland' and tech == 'Solar':
                continue
            # Suma de generación por año
            gen_sum = combined.resample('YE')[tech].sum()
            # Precio capturado anual
            cap_price = combined.resample('YE').apply(
                lambda x: (x['Price'] * x[tech]).sum() / x[tech].sum() if x[tech].sum() != 0 else None
            )
            yearly[f'{tech} Generation'] = gen_sum
            yearly[f'{tech} Capture Price'] = cap_price
            yearly[f'{tech} Capture %'] = cap_price / yearly['Price']

        capture_results[country] = yearly

    return capture_results

def merge_capture_data(old_data: dict, new_data: dict) -> dict:
    """
    Combina dos diccionarios de DataFrames con claves por país.
    Concatena, ordena por fecha y elimina duplicados por índice.

    Parámetros:
    - old_data: dict con datos históricos por país.
    - new_data: dict con nuevos datos por país.

    Retorna:
    - dict con los datos combinados.
    """
    combined = {}

    for country in old_data:
        # Obtener los dataframes antiguos y nuevos
        old_df = old_data[country]
        new_df = new_data.get(country)

        # Asegurar que los índices sean fechas
        old_df.index = pd.to_datetime(old_df.index)
        if new_df is not None:
            new_df.index = pd.to_datetime(new_df.index)

            # Concatenar y limpiar duplicados
            merged_df = pd.concat([old_df, new_df])
            merged_df = merged_df[~merged_df.index.duplicated(keep='last')]
            merged_df = merged_df.sort_index()
        else:
            merged_df = old_df

        combined[country] = merged_df

    # Agregar nuevos países que no estaban en old_data
    for country in new_data:
        if country not in old_data:
            new_df = new_data[country]
            new_df.index = pd.to_datetime(new_df.index)
            combined[country] = new_df.sort_index()

    return combined


def plot_cross_country_correlation_heatmap(monthly_capture_prices):
    """
    Genera un único mapa de calor con las correlaciones entre tasas de captura (%)
    y generación de Solar y Wind Onshore, distinguiendo por país.
    
    Muestra los valores en formato porcentaje y usa una figura más ancha que alta.
    """
    dfs = []
    all_cols = ['Wind Onshore Generation', 'Wind Onshore Capture %',
                'Solar Generation', 'Solar Capture %']

    for country, df in monthly_capture_prices.items():
        available_cols = [col for col in all_cols if col in df.columns]
        if not available_cols:
            print(f"[WARN] {country}: No columnas relevantes encontradas, se omite.")
            continue

        temp_df = df[available_cols].copy()
        temp_df.columns = [f"{country}_{col}" for col in temp_df.columns]
        dfs.append(temp_df.reset_index(drop=True))

    if not dfs:
        print("No hay datos disponibles para construir el mapa de calor.")
        return

    # Truncar a la mínima longitud para alinear
    min_len = min(len(df) for df in dfs)
    dfs_aligned = [df.iloc[:min_len] for df in dfs]

    # Unir columnas horizontalmente
    merged_df = pd.concat(dfs_aligned, axis=1)

    # Calcular matriz de correlación
    corr_matrix = merged_df.corr()

    # Visualizar mapa de calor (más ancho que alto)
    n = len(corr_matrix)
    plt.figure(figsize=(max(16, n * 0.6), max(8, n * 0.4)))

    sns.heatmap(
        corr_matrix,
        cmap='crest',
        annot=True,
        fmt=".0%",
        cbar=True,
        square=False
    )
    plt.title('Correlaciones entre Capture % y Generation (Todos los países)', fontsize=14)
    plt.xticks(rotation=90)
    plt.yticks(rotation=0)
    plt.tight_layout()
    plt.show()
