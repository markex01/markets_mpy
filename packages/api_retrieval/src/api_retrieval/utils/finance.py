import pandas as pd
from typing import List, Dict, Optional, Union


class InflationAdjuster:
    """
    A modular helper class for adjusting currency values based on inflation rates.
    Supports both monthly and yearly inflation adjustments.
    
    Attributes:
        inflation_df (pd.DataFrame): DataFrame containing inflation data with columns:
            - 'Country': Country name
            - 'Date': Date of inflation data
            - 'Type': Type of inflation data ('Inflation (annual % change)', etc.)
            - Year columns (e.g., 2015, 2016, ...) with inflation rates
        country (str): Default country for inflation adjustments
        date_filter (str): Default date filter for selecting inflation data
    """
    
    def __init__(
        self, 
        inflation_df: pd.DataFrame,
        country: str = 'Spain',
        date_filter: str = '2025-Apr'
    ):
        """
        Initialize the InflationAdjuster with inflation data.
        
        Args:
            inflation_df: DataFrame containing inflation data
            country: Default country for adjustments
            date_filter: Default date to filter latest inflation data
        """
        self.inflation_df = inflation_df
        self.country = country
        self.date_filter = date_filter
        self._inflation_map_cache = {}
    
    def _get_inflation_map(
        self, 
        country: Optional[str] = None,
        date_filter: Optional[str] = None,
        inflation_type: str = 'Inflation (annual % change)'
    ) -> Dict[int, float]:
        """
        Extract inflation map from the inflation DataFrame.
        
        Args:
            country: Country to filter (uses default if None)
            date_filter: Date to filter (uses default if None)
            inflation_type: Type of inflation data to extract
            
        Returns:
            Dictionary mapping year to inflation rate percentage
        """
        country = country or self.country
        date_filter = date_filter or self.date_filter
        
        # Check cache
        cache_key = (country, date_filter, inflation_type)
        if cache_key in self._inflation_map_cache:
            return self._inflation_map_cache[cache_key]
        
        # Filter inflation data
        inflation_df_fil = self.inflation_df[
            (self.inflation_df['Country'] == country)
            & (self.inflation_df['Date'] == date_filter)
            & (self.inflation_df['Type'] == inflation_type)
        ]
        
        if inflation_df_fil.empty:
            raise ValueError(
                f"No inflation data found for {country} at {date_filter} "
                f"with type '{inflation_type}'"
            )
        
        # Extract inflation map
        inflation_row = inflation_df_fil.iloc[0]
        non_year_cols = ['Country', 'Date', 'Type']
        inflation_map = {
            int(col): float(inflation_row[col])
            for col in inflation_row.index
            if col not in non_year_cols and pd.notna(inflation_row[col])
        }
        
        # Cache result
        self._inflation_map_cache[cache_key] = inflation_map
        
        return inflation_map
    
    @staticmethod
    def adjust_yearly(
        value: float,
        inflation_map: Dict[int, float],
        target_year: int,
        base_year: int
    ) -> float:
        """
        Convert a value from base_year prices to target_year prices using annual rates.
        
        Args:
            value: The monetary value to adjust
            inflation_map: Dictionary mapping year to inflation rate (in percent)
            target_year: Year to convert to
            base_year: Year to convert from
            
        Returns:
            Adjusted value in target_year prices
        """
        def r(y: int) -> float:
            if y not in inflation_map:
                raise KeyError(f"Missing annual rate (percent) for year {y}")
            return float(inflation_map[y]) / 100.0
        
        # Forward: from Dec(base_year) -> Dec(target_year)
        if target_year > base_year:
            factor = 1.0
            for y in range(base_year + 1, target_year + 1):
                factor *= (1.0 + r(y))
            return value * factor
        
        # Same year
        if target_year == base_year:
            return value
        
        # Backward: from Dec(base_year) -> Dec(target_year)
        factor_forward = 1.0
        for y in range(target_year + 1, base_year + 1):
            factor_forward *= (1.0 + r(y))
        return value / factor_forward
    
    @staticmethod
    def adjust_monthly(
        value: float,
        inflation_map: Dict[int, float],
        target_month: int,
        target_year: int,
        base_year: int
    ) -> float:
        """
        Convert a value from Dec(base_year) to (target_year, target_month) using annual rates.
        
        Args:
            value: The monetary value to adjust
            inflation_map: Dictionary mapping year to inflation rate (in percent)
            target_month: Target month (1-12)
            target_year: Target year
            base_year: Base year (December reference)
            
        Returns:
            Adjusted value in target_year/target_month prices
        """
        if not (1 <= target_month <= 12):
            raise ValueError("target_month must be in 1..12")
        
        def r(y: int) -> float:
            if y not in inflation_map:
                raise KeyError(f"Missing annual rate (percent) for year {y}")
            return float(inflation_map[y]) / 100.0
        
        # Forward: from Dec(base_year) -> (target_year, target_month)
        if target_year > base_year:
            factor = 1.0
            # Full years between base_year and target_year
            for y in range(base_year + 1, target_year):
                factor *= (1.0 + r(y))
            # Partial year within target_year
            factor *= (1.0 + r(target_year)) ** (target_month / 12.0)
            return value * factor
        
        # Same year
        if target_year == base_year:
            return value
        
        # Backward
        factor_forward = 1.0
        factor_forward *= (1.0 + r(target_year)) ** ((12 - target_month) / 12.0)
        for y in range(target_year + 1, base_year):
            factor_forward *= (1.0 + r(y))
        factor_forward *= (1.0 + r(base_year))
        return value / factor_forward
    
    def transform_to_real_prices_yearly(
        self,
        df: pd.DataFrame,
        base_year: int,
        year_col: str = 'year',
        price_cols: List[str] = None,
        country_col: Optional[str] = None,
        date_filter: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Transform nominal prices to real prices using yearly inflation adjustments.
        
        Args:
            df: DataFrame with prices and 'currency' column (e.g., 'EUR2023')
            base_year: Reference year for real prices
            year_col: Column name containing target years
            price_cols: List of price columns to transform
            country_col: Column name containing country information (uses default if None)
            date_filter: Date filter for inflation data (uses default if None)
            
        Returns:
            DataFrame with additional 'nominal_{col}' columns and 'real_{col}_{base_year}' columns
        """
        df = df.copy()
        df['currency_year'] = df['currency'].str[-4:].astype(int)
        
        if price_cols is None:
            price_cols = ['solar_capture', 'onshore_wind_capture']
        
        
        def _apply_row(row, price_col, target_year=None):
            # Get inflation map
            inflation_map = self._get_inflation_map(row[country_col] if country_col else None, date_filter)
            return self.adjust_yearly(
                value=row[price_col],
                inflation_map=inflation_map,
                target_year=target_year if target_year is not None else int(row[year_col]),
                base_year=int(row["currency_year"])
            )
        
        for col in price_cols:
            df[col] = df[col].astype(float)
            df[f'nominal_{col}'] = df.apply(_apply_row, axis=1, args=(col,))
        
        # Now we get real prices, according to base_year
        for col in price_cols:
            df[f'real_{col}_{base_year}'] = df.apply(_apply_row, axis=1, args=(col, base_year))
        return df.reset_index(drop=True)
    
    def transform_to_real_prices_monthly(
        self,
        df: pd.DataFrame,
        base_year: int,
        year_col: str = 'year',
        month_col: str = 'month',
        price_cols: List[str] = None,
        country_col: Optional[str] = None,
        date_filter: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Transform nominal prices to real prices using monthly inflation adjustments.
        
        Args:
            df: DataFrame with prices and 'currency' column
            base_year: Reference year for real prices
            year_col: Column name containing target years
            month_col: Column name containing target months
            price_cols: List of price columns to transform
            country_col: Column name containing country information (uses default if None)
            date_filter: Date filter for inflation data (uses default if None)
            
        Returns:
            DataFrame with additional 'nominal_{col}' columns and 'real_{col}_{base_year}' columns
        """
        df = df.copy()
        df['currency_year'] = df['currency'].str[-4:].astype(int)
        
        if price_cols is None:
            price_cols = ['solar_capture', 'onshore_wind_capture']
        
        # Get inflation map
        
        def _apply_row(row, price_col, target_year=None):
            inflation_map = self._get_inflation_map(row[country_col] if country_col else None, date_filter)
            return self.adjust_monthly(
                value=row[price_col],
                inflation_map=inflation_map,
                target_month=int(row[month_col]),
                target_year=target_year if target_year is not None else int(row[year_col]),
                base_year=int(row["currency_year"])
            )
        
        for col in price_cols:
            df[col] = df[col].astype(float)
            df[f'nominal_{col}'] = df.apply(_apply_row, axis=1, args=(col,))
        
        for col in price_cols:
            df[f'real_{col}_{base_year}'] = df.apply(_apply_row, axis=1, args=(col, base_year))
        
        return df.reset_index(drop=True)
    
    def create_conversion_table(
        self,
        base_year: int,
        country: Optional[str] = None,
        date_filter: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Create a table of conversion factors between base_year and all available years.
        
        Args:
            base_year: Reference year
            country: Country for inflation data (uses default if None)
            date_filter: Date filter for inflation data (uses default if None)
            
        Returns:
            DataFrame with conversion factors for each year
        """
        inflation_map = self._get_inflation_map(country, date_filter)
        years = sorted(inflation_map.keys())
        
        conversion_data = []
        
        for target_year in years:
            # From base_year to target_year
            to_nominal_factor = self.adjust_yearly(
                value=1.0,
                inflation_map=inflation_map,
                target_year=target_year,
                base_year=base_year
            )
            
            # From target_year to base_year
            from_nominal_factor = self.adjust_yearly(
                value=1.0,
                inflation_map=inflation_map,
                target_year=base_year,
                base_year=target_year
            )
            
            conversion_data.append({
                'year': target_year,
                'to_nominal_from_base': to_nominal_factor,
                'to_real_from_base': from_nominal_factor,
                'from_nominal_to_base': from_nominal_factor,
                'from_real_to_base': to_nominal_factor
            })
        
        return pd.DataFrame(conversion_data)
    
    def create_indices_table(
        self,
        base_year: int,
        country: Optional[str] = None,
        date_filter: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Create inflation indices table (Index to real/nominal format).
        
        Args:
            base_year: Reference year where indices = 1.0
            country: Country for inflation data (uses default if None)
            date_filter: Date filter for inflation data (uses default if None)
            
        Returns:
            DataFrame with 'index_to_real_{base_year}' and 'index_to_nominal' columns
        """
        inflation_map = self._get_inflation_map(country, date_filter)
        years = sorted(inflation_map.keys())
        
        results = []
        
        for target_year in years:
            # Index to nominal: base_year real -> target_year nominal
            index_to_nominal = self.adjust_yearly(
                value=1.0,
                inflation_map=inflation_map,
                target_year=target_year,
                base_year=base_year
            )
            
            # Index to real: target_year nominal -> base_year real
            index_to_real = self.adjust_yearly(
                value=1.0,
                inflation_map=inflation_map,
                target_year=base_year,
                base_year=target_year
            )
            
            results.append({
                'year': target_year,
                'inflation_annual_pct': inflation_map[target_year],
                f'index_to_real_{base_year}': index_to_real,
                'index_to_nominal': index_to_nominal
            })
        
        return pd.DataFrame(results)
    
    def create_conversion_table_all_countries(
        self,
        base_year: int,
        date_filter: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Create inflation indices table for all available countries and all release dates with years as columns.
        
        Args:
            base_year: Reference year where indices = 1.0
            date_filter: Date filter for inflation data (if None, processes ALL releases)
            
        Returns:
            DataFrame with:
                - Rows: inflation_annual_pct_{country}_{release}, 
                        index_to_real_{base_year}_{country}_{release}, 
                        index_to_nominal_{country}_{release}
                - Columns: years (2015, 2016, 2017, ...)
        """
        # If date_filter is None, get all available release dates
        if date_filter is None:
            # Get all unique combinations of Country and Date
            country_date_combinations = self.inflation_df[
                self.inflation_df['Type'] == 'Inflation (annual % change)'
            ][['Country', 'Date']].drop_duplicates()
        else:
            # Use specific date filter
            country_date_combinations = self.inflation_df[
                (self.inflation_df['Type'] == 'Inflation (annual % change)') &
                (self.inflation_df['Date'] == date_filter)
            ][['Country', 'Date']].drop_duplicates()
        
        all_data = []
        
        for _, row in country_date_combinations.iterrows():
            country = row['Country']
            release_date = row['Date']
            
            # Create release suffix from date (e.g., '2025-Apr' -> 'Apr_2025')
            # release_suffix = release_date.replace('-', '_')
            
            try:
                # Get inflation map for this country and release
                inflation_map = self._get_inflation_map(
                    country=country,
                    date_filter=release_date
                )
                
                years = sorted(inflation_map.keys())
                
                # Initialize dictionaries for this country/release combination
                inflation_pct_row = {
                    'metric': f'{country}-{release_date}-Inflation (annual % change)'
                }
                index_to_real_row = {
                    'metric': f'{country}-{release_date}-Index to real {base_year}'
                }
                index_to_nominal_row = {
                    'metric': f'{country}-{release_date}-Index to nominal {base_year}'
                }
                
                # Calculate indices for each year
                for target_year in years:
                    # Inflation percentage
                    inflation_pct_row[target_year] = inflation_map[target_year]
                    
                    # Index to nominal: base_year real -> target_year nominal
                    index_to_nominal = self.adjust_yearly(
                        value=1.0,
                        inflation_map=inflation_map,
                        target_year=target_year,
                        base_year=base_year
                    )
                    index_to_nominal_row[target_year] = index_to_nominal
                    
                    # Index to real: target_year nominal -> base_year real
                    index_to_real = self.adjust_yearly(
                        value=1.0,
                        inflation_map=inflation_map,
                        target_year=base_year,
                        base_year=target_year
                    )
                    index_to_real_row[target_year] = index_to_real
                
                # Add rows for this country/release
                all_data.append(inflation_pct_row)
                all_data.append(index_to_real_row)
                all_data.append(index_to_nominal_row)
                
            except (ValueError, KeyError) as e:
                # Skip combinations with missing data
                print(f"Skipping {country} ({release_date}): {e}")
                continue
        
        # Create DataFrame
        result_df = pd.DataFrame(all_data)
        
        # Set 'metric' as index
        result_df = result_df.set_index('metric')
        
        # Sort year columns
        year_cols = [col for col in result_df.columns if isinstance(col, int)]
        result_df = result_df[sorted(year_cols)]
        
        return result_df


    # Alternative method to get only specific releases
    def create_conversion_table_specific_releases(
        self,
        base_year: int,
        country_date_map: Dict[str, List[str]]
    ) -> pd.DataFrame:
        """
        Create inflation indices table for specific countries and their release dates.
        
        Args:
            base_year: Reference year where indices = 1.0
            country_date_map: Dictionary mapping country to list of release dates
                            e.g., {'Spain': ['2025-Apr', '2024-Oct'], 'Germany': ['2025-Apr']}
            
        Returns:
            DataFrame with rows for each country/release combination and years as columns
        """
        all_data = []
        
        for country, release_dates in country_date_map.items():
            for release_date in release_dates:
                # Create release suffix
                release_suffix = release_date.replace('-', '_')
                
                try:
                    # Get inflation map for this country and release
                    inflation_map = self._get_inflation_map(
                        country=country,
                        date_filter=release_date
                    )
                    
                    years = sorted(inflation_map.keys())
                    
                    # Initialize dictionaries
                    inflation_pct_row = {
                        'metric': f'inflation_annual_pct_{country}_{release_suffix}'
                    }
                    index_to_real_row = {
                        'metric': f'index_to_real_{base_year}_{country}_{release_suffix}'
                    }
                    index_to_nominal_row = {
                        'metric': f'index_to_nominal_{country}_{release_suffix}'
                    }
                    
                    # Calculate indices for each year
                    for target_year in years:
                        inflation_pct_row[target_year] = inflation_map[target_year]
                        
                        index_to_nominal = self.adjust_yearly(
                            value=1.0,
                            inflation_map=inflation_map,
                            target_year=target_year,
                            base_year=base_year
                        )
                        index_to_nominal_row[target_year] = index_to_nominal
                        
                        index_to_real = self.adjust_yearly(
                            value=1.0,
                            inflation_map=inflation_map,
                            target_year=base_year,
                            base_year=target_year
                        )
                        index_to_real_row[target_year] = index_to_real
                    
                    all_data.append(inflation_pct_row)
                    all_data.append(index_to_real_row)
                    all_data.append(index_to_nominal_row)
                    
                except (ValueError, KeyError) as e:
                    print(f"Skipping {country} ({release_date}): {e}")
                    continue
        
        result_df = pd.DataFrame(all_data)
        result_df = result_df.set_index('metric')
        
        year_cols = [col for col in result_df.columns if isinstance(col, int)]
        result_df = result_df[sorted(year_cols)]
        
        return result_df


# Example usage:
# adjuster = InflationAdjuster(
#     inflation_df=inflation_figures_df,
#     country='Spain',
#     date_filter='2025-Apr'
# )
#
# # Get ALL countries and ALL releases
# all_releases_table = adjuster.create_conversion_table_all_countries(
#     base_year=2025,
#     date_filter=None  # None means get all releases
# )
#
# # Get specific releases only
# specific_table = adjuster.create_conversion_table_specific_releases(
#     base_year=2025,
#     country_date_map={
#         'Spain': ['2025-Apr', '2024-Oct', '2024-Apr'],
#         'Germany': ['2025-Apr', '2024-Dec'],
#         'France': ['2025-Apr']
#     }
# )


# Example usage:
# adjuster = InflationAdjuster(
#     inflation_df=inflation_figures_df,
#     country='Spain',
#     date_filter='2025-Apr'
# )
#
# all_countries_table = adjuster.create_conversion_table_all_countries(
#     base_year=2025,
#     date_filter='2025-Apr'
# )
#
# print(all_countries_table)




# Example usage:
# adjuster = InflationAdjuster(
#     inflation_df=inflation_figures_df,
#     country='Spain',
#     date_filter='2025-Apr'
# )
#
# # Transform dataframe
# df_adjusted = adjuster.transform_to_real_prices_yearly(
#     df=my_dataframe,
#     base_year=2025,
#     price_cols=['solar_capture', 'onshore_wind_capture']
# )
#
# # Get conversion table
# conversion_table = adjuster.create_conversion_table(base_year=2025)
#
# # Get indices table
# indices = adjuster.create_indices_table(base_year=2025)
