from bloomberg.api_helper.extractor import BloombergExtractor as BE
from common_libs.utils.utils_dates import get_start_date_from_quarterly
import pandas as pd

class QuarterlyDataExtractor:
    """Extracts and aggregates Bloomberg market data for quarterly reporting.

    Opens a Bloomberg session per data call and builds monthly summary
    DataFrames (normalized or absolute) suitable for ThinkCell export.

    Attributes:
        be: BloombergExtractor instance (unused by current methods; kept for
            subclass compatibility).
        europe_daily_pool_securities: Mapping of identifier → Bloomberg ticker
            for daily pool price retrieval.
        europe_hourly_pool_security_roots: Mapping of identifier → Bloomberg
            ticker root for hourly pool price retrieval.
        power_prices_path: Default Excel export path for power price data.
        start_date: Start of the quarter derived from ``quarter`` (set only
            when ``quarter`` is provided at construction).
        end_date: End of the quarter derived from ``quarter`` (set only when
            ``quarter`` is provided at construction).
    """

    def __init__(
            self,
            Extractor: BE = None,
            quarter: str = None,
            europe_daily_pool_securities: dict = None,
            europe_hourly_pool_security_roots: dict = None,
            power_prices_path: str = None
        ):
        """Initialises the extractor with optional securities dictionaries and date range.

        Args:
            Extractor: BloombergExtractor class (or compatible factory). A new
                ``BE`` instance is created if not provided. The instance is
                stored but not used by the built-in retrieval methods.
            quarter: Quarterly string in ``"YYQX"`` format (e.g. ``"25Q4"``).
                When provided, ``start_date`` and ``end_date`` are derived
                automatically via :func:`get_start_date_from_quarterly`.
            europe_daily_pool_securities: Mapping of country/identifier →
                full Bloomberg ticker (e.g. ``{"ESP": "MIBGAS D Index"}``).
            europe_hourly_pool_security_roots: Mapping of identifier →
                Bloomberg ticker root for hourly data retrieval.
            power_prices_path: Default output path for Excel exports.
        """
        self.be = Extractor() if Extractor else BE()

        # Set security dictionaries
        self.europe_daily_pool_securities = europe_daily_pool_securities
        self.europe_hourly_pool_security_roots = europe_hourly_pool_security_roots

        # Set paths for data export
        self.power_prices_path = power_prices_path

        if quarter:
            start_date, end_date = get_start_date_from_quarterly(quarter)
            self.start_date = start_date
            self.end_date = end_date

    # ==================== Helpers ====================

    def _export_to_excel(self, df: pd.DataFrame, file_path: str):
        """Exports the given DataFrame to an Excel file. File is transposed for adaption to ThinkCell format.
        Args:
            df (pd.DataFrame): DataFrame to be exported.
            file_path (str): Path to the output Excel file.
        """
        df.T.to_excel(file_path)

    def _get_data(self, start_date: str = None, end_date: str = None, securities_dict: dict = None, periodicity: str = 'D') -> pd.DataFrame:
        """Retrieves Bloomberg historical price data for a set of securities.

        Opens a Bloomberg session, calls ``BDH`` for each security in
        ``securities_dict``, appends the currency via ``BDP``, and returns
        all results concatenated into a single tidy DataFrame.

        Args:
            start_date: Start date in ``"YYYY-MM-DD"`` format. Falls back to
                ``self.start_date`` if not provided.
            end_date: End date in ``"YYYY-MM-DD"`` format. Falls back to
                ``self.end_date`` if not provided.
            securities_dict: Mapping of ``country_id`` → full Bloomberg ticker.
                Falls back to ``self.europe_daily_pool_securities`` if not
                provided.
            periodicity: Bloomberg periodicity code (``"D"`` for daily,
                ``"M"`` for monthly, etc.). Defaults to ``"D"``.

        Returns:
            DataFrame with columns ``["date", "country_id", "price", "ccy"]``,
            concatenated across all securities in ``securities_dict``.

        Raises:
            ValueError: If ``start_date`` or ``end_date`` cannot be resolved
                from arguments or instance attributes.
            ValueError: If ``securities_dict`` cannot be resolved from
                arguments or ``self.europe_daily_pool_securities``.
        """
        if not start_date:
            start_date = self.start_date
        if not end_date:
            end_date = self.end_date

        if not start_date or not end_date:
            raise ValueError("start_date and end_date must be provided either during initialization or as arguments.")

        if securities_dict is None:
            securities_dict = self.europe_daily_pool_securities

        if not securities_dict:
            raise ValueError("A securities_dict must be provided either as an argument or via europe_daily_pool_securities.")

        df = pd.DataFrame()

        with BE() as bb:
            for country_id, security in securities_dict.items():
                # security = security + " Index"
                print(f"Retrieving data for {country_id} - {security} from {start_date} to {end_date}...")
                data = bb.bdh(
                    security=security,
                    fields=["PX_LAST"],
                    start=start_date,
                    end=end_date,
                    periodicity=periodicity
                )
                print(f"Data retrieved for {country_id} - {security}. Retrieving currency information...")
                ccy = bb.bdp(
                    securities=[security],
                    fields=["CRNCY"]
                ).loc[security, "CRNCY"]
                print(f"Currency for {country_id} - {security}: {ccy}")
                data['ccy'] = ccy
                data['country_id'] = country_id
                data.rename(columns={"PX_LAST": "price"}, inplace=True)
                print(data.head())
                data = data[['date', 'country_id', 'price', 'ccy']]
                df = pd.concat([df, data], ignore_index=True)

        return df
    
    def build_monthly_normalized_df(self, start_date: str = None, end_date: str = None, securities_dict: dict = None, export_path: str = None, periodicity: str = 'D') -> pd.DataFrame:
        """Builds a DataFrame containing normalized monthly data for the specified date range and securities.
        Args:
            start_date (str, optional): Start date in the format "YYYY-MM-DD". Defaults to None.
            end_date (str, optional): End date in the format "YYYY-MM-DD". Defaults to None.
            securities_dict (dict, optional): Dictionary mapping identifiers to Bloomberg security roots.
                Falls back to self.europe_daily_pool_securities if not provided.
            export_path (str, optional): Path to export the DataFrame to Excel. Defaults to None.
        Returns:
            pd.DataFrame: DataFrame containing normalized monthly data with columns ['date', identifier columns].
        """
        # Retrieve daily data for the specified date range
        monthly_pool_df = self._get_data(start_date, end_date, securities_dict, periodicity=periodicity)

        # Convert date column to datetime format for time-based operations
        monthly_pool_df['date'] = pd.to_datetime(monthly_pool_df['date'])
        
        # Group by country_id and year-month, then calculate the mean price for each group
        ds = monthly_pool_df.groupby([monthly_pool_df['country_id'], monthly_pool_df['date'].dt.year, monthly_pool_df['date'].dt.month])['price'].mean()
        ds.index.names = ['country_id', 'year', 'month']
        
        # Reset index to convert grouped series into a DataFrame
        df_month = ds.reset_index()
        
        # Pivot the DataFrame: rows = year-month, columns = country_id (one column per country)
        df_month = df_month.pivot(index=['year', 'month'], columns='country_id', values='price').reset_index()

        # Create a date column representing the first day of each month
        df_month['date'] = pd.to_datetime(df_month[['year', 'month']].assign(day=1))
        df_month['date'] = df_month['date'].dt.date

        # Set date as index and remove the temporary year/month columns
        df_month.set_index('date', inplace=True)
        df_month = df_month.drop(columns=['year', 'month'])
        
        # Reset index to make date a regular column for the normalization step
        df_month.reset_index(inplace=True)

        # Normalize the dataframe based on the first available month's values
        # 1) sort
        df = df_month.sort_values("date").reset_index(drop=True)
        # 2) separate numeric part and coerce to numeric
        num = df.drop(columns=["date"]).apply(pd.to_numeric, errors="coerce")
        # 3) normalize by the first row (base)
        base = num.iloc[0]
        num_norm = num.divide(base)
        # 4) stitch back together
        df_power_normalized = pd.concat([df[["date"]], num_norm], axis=1)

        # Export to Excel if path is provided
        if export_path:
            self._export_to_excel(df_power_normalized, export_path)
        
        return df_power_normalized.T

    def build_monthly_absolute_df(self, start_date: str = None, end_date: str = None, securities_dict: dict = None, export_path: str = None, periodicity: str = 'D') -> pd.DataFrame:
        """Builds a DataFrame containing monthly average prices in absolute values.
        Args:
            start_date (str, optional): Start date in the format "YYYY-MM-DD". Defaults to None.
            end_date (str, optional): End date in the format "YYYY-MM-DD". Defaults to None.
            securities_dict (dict, optional): Dictionary mapping identifiers to Bloomberg security roots.
                Falls back to self.europe_daily_pool_securities if not provided.
            export_path (str, optional): Path to export the DataFrame to Excel. Defaults to None.
        Returns:
            pd.DataFrame: DataFrame with columns ['date', identifier columns] containing absolute monthly average prices.
        """
        # Retrieve daily data for the specified date range
        daily_df = self._get_data(start_date, end_date, securities_dict, periodicity=periodicity)

        # Convert date column to datetime format for time-based operations
        daily_df['date'] = pd.to_datetime(daily_df['date'])

        # Group by country_id and year-month, then calculate the mean price for each group
        ds = daily_df.groupby([daily_df['country_id'], daily_df['date'].dt.year, daily_df['date'].dt.month])['price'].mean()
        ds.index.names = ['country_id', 'year', 'month']

        # Reset index to convert grouped series into a DataFrame
        df_month = ds.reset_index()

        # Pivot the DataFrame: rows = year-month, columns = country_id (one column per country)
        df_month = df_month.pivot(index=['year', 'month'], columns='country_id', values='price').reset_index()

        # Create a date column representing the last day of each month
        df_month['date'] = pd.to_datetime(df_month[['year', 'month']].assign(day=1))
        df_month['date'] = df_month['date'].dt.date

        # Set date as index and remove the temporary year/month columns
        df_month.set_index('date', inplace=True)
        df_month = df_month.drop(columns=['year', 'month'])
        df_month.reset_index(inplace=True)

        # Sort by date
        df_month = df_month.sort_values("date").reset_index(drop=True)

        # Export to Excel if path is provided
        if export_path:
            self._export_to_excel(df_month, export_path)

        return df_month.T
    