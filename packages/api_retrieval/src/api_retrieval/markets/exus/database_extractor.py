import pyodbc
import pandas as pd

class DatabaseExtractor:
    def __init__(self, server: str, username: str, password: str, driver: str = "SQL Server"):
        self.server = server
        self.username = username
        self.password = password
        self.driver = driver

    def _connect(self, database: str):
        conn_str = (
            f"DRIVER={{{self.driver}}};"
            f"SERVER={self.server};"
            f"DATABASE={database};"
            f"UID={self.username};"
            f"PWD={self.password};"
            "Connection Timeout=30;"
        )
        return pyodbc.connect(conn_str)


    def list_databases(self) -> list[str]:
        conn = self._connect("master")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sys.databases;")
        dbs = [row.name for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return dbs

    def list_tables(self, database: str) -> list[str]:
        conn = self._connect(database)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT TABLE_SCHEMA, TABLE_NAME "
            "FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE';"
        )
        tables = [f"{row.TABLE_SCHEMA}.{row.TABLE_NAME}" for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return tables

    def list_columns(self, database: str, table: str) -> list[str]:
            conn = self._connect(database)
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = '{table.split('.')[-1]}'
                """
            )
            cols = [row.COLUMN_NAME for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return cols

    def query_table(
        self,
        database: str,
        table: str,
        filters: dict = None,
        limit: int = None,
        order_by: str = None,
        columns: list[str] = None
    ) -> pd.DataFrame:

        conn = self._connect(database)

        cols = ", ".join(columns) if columns else "*"
        top_clause = f"TOP {limit} " if limit else ""
        query = f"SELECT {top_clause}{cols} FROM {table}"

        if filters:
            conditions = []

            for col, val in filters.items():
                if isinstance(val, (list, tuple, set)):
                    formatted_vals = ", ".join(f"'{v}'" for v in val)
                    conditions.append(f"{col} IN ({formatted_vals})")
                else:
                    conditions.append(f"{col} = '{val}'")

            query += " WHERE " + " AND ".join(conditions)

        if order_by:
            query += f" ORDER BY {order_by}"

        df = pd.read_sql(query, conn)
        conn.close()
        return df


    def query_crossborder_flows(
        self,
        country: str,
        direction: str,
        start: str = None,
        end: str = None,
        resolution: str = None
    ) -> pd.DataFrame:
        """
        Query cross-border flows for a given country.
        direction: 'imports' (flows INTO country) or 'exports' (flows FROM country)
        start/end: date strings in YYYYMMDD format
        resolution: e.g. 'PT60M', 'PT15M' — if None, all resolutions are returned
        """
        if direction == "imports":
            filter_col = "CountryCodeTo"
        elif direction == "exports":
            filter_col = "CountryCodeFrom"
        else:
            raise ValueError("direction must be 'imports' or 'exports'")

        conn = self._connect("bigcloud_db")
        query = (
            f"SELECT * FROM dbo.EuropeInterconnectionActuals "
            f"WHERE {filter_col} = '{country}'"
        )
        if resolution:
            query += f" AND Resolution = '{resolution}'"
        if start:
            start_dt = pd.to_datetime(start, format="%Y%m%d")
            query += f" AND UTCTime >= '{start_dt}'"
        if end:
            end_dt = pd.to_datetime(end, format="%Y%m%d") + pd.Timedelta(days=1)
            query += f" AND UTCTime < '{end_dt}'"

        df = pd.read_sql(query, conn)
        conn.close()
        df["Direction"] = direction
        return df

    def build_master_df(self, db, country: str = "ES"):
        # --- Helpers ---
        def _to_utc_naive(s):
            dt = pd.to_datetime(s, errors="coerce", utc=True)
            return dt.dt.tz_convert(None) if hasattr(dt, "dt") else dt.tz_convert(None)

        def _series_prioritize_pt60m(df, value_col="Quantity"):
            df = df.copy()
            df["UTCTime"] = _to_utc_naive(df["UTCTime"])

            # Prefer PT60M
            s60 = (
                df[df["Resolution"] == "PT60M"]
                .groupby("UTCTime")[value_col]
                .mean()
                .sort_index()
            )

            # Fallback: PT15M aggregated to hourly
            s15 = (
                df[df["Resolution"] == "PT15M"]
                .set_index("UTCTime")[value_col]
                .groupby(level=0).mean()
                .resample("H").mean()
                .sort_index()
            )

            return s60.combine_first(s15).groupby(level=0).mean()

        def _gen_prioritize_pt60m(df):
            df = df.copy()
            df["UTCTime"] = _to_utc_naive(df["UTCTime"])

            g60 = (
                df[df["Resolution"] == "PT60M"]
                .pivot_table(index="UTCTime", columns="Technology", values="Quantity", aggfunc="mean")
            )
            g15 = (
                df[df["Resolution"] == "PT15M"]
                .pivot_table(index="UTCTime", columns="Technology", values="Quantity", aggfunc="mean")
                .resample("H").mean()
            )

            gen = g60.combine_first(g15).sort_index()
            gen = gen.groupby(level=0).mean()
            gen.columns = [f"Gen_{c}" for c in gen.columns]
            return gen

        def _cap_expand_hourly(df, demand_index):
            df = df.copy()
            df["UTCTime"] = _to_utc_naive(df["UTCTime"])

            if df.empty:
                return pd.DataFrame(index=demand_index)

            # Each record (31-Dec-YYYY) -> applies to all hours of YYYY+1
            df["YearApply"] = df["UTCTime"].dt.year + 1

            # One capacity per technology per year
            cap_year = (
                df.groupby(["YearApply", "Technology"])["Quantity"]
                .mean()
                .unstack("Technology")
                .sort_index()
            )

            # Build full hourly index limited to demand period
            dt_start = demand_index.min().floor("H")
            dt_end = demand_index.max().ceil("H")
            hourly_index = pd.date_range(dt_start, dt_end, freq="H")

            # Expand each year's value to all hours of that year
            expanded = []
            for year, row in cap_year.iterrows():
                start = pd.Timestamp(year=year, month=1, day=1, hour=0)
                end = pd.Timestamp(year=year, month=12, day=31, hour=23)
                idx = pd.date_range(start, end, freq="H")
                block = pd.DataFrame([row.values] * len(idx), index=idx, columns=cap_year.columns)
                expanded.append(block)

            cap_hourly = pd.concat(expanded).sort_index()

            # Restrict strictly to demand range
            cap_hourly = cap_hourly.reindex(hourly_index)

            cap_hourly.columns = [f"Cap_{c}" for c in cap_hourly.columns]
            return cap_hourly


        # --- Demand (anchor index) ---
        df_dem = db.query_table(
            "bigcloud_db",
            "dbo.EuropeDemandActuals",
            filters={"CountryCode": country, "Type": "Actual"},
            order_by="UTCTime DESC",
            columns=["CountryCode", "UTCTime", "Quantity", "Unit", "Resolution"],
        )
        dem = _series_prioritize_pt60m(df_dem, "Quantity").to_frame("Demand")

        # --- Generation ---
        df_gen = db.query_table(
            "bigcloud_db",
            "dbo.EuropeGenerationActuals",
            filters={"CountryCode": country},
            order_by="UTCTime DESC",
            columns=["CountryCode", "Technology", "UTCTime", "Quantity", "Unit", "Resolution"],
        )
        gen = _gen_prioritize_pt60m(df_gen)

        # --- Capacity ---
        df_cap = db.query_table(
            "bigcloud_db",
            "dbo.EuropeCapacityActuals",
            filters={"CountryCode": country},
            order_by="UTCTime DESC",
            columns=["CountryCode", "UTCTime", "Technology", "Quantity", "Unit", "Resolution"],
        )
        cap = _cap_expand_hourly(df_cap, dem.index)

        # --- Imports ---
        df_imp = db.query_table(
            "bigcloud_db",
            "dbo.EuropeInterconnectionActuals",
            filters={"CountryCodeTo": country},
            order_by="UTCTime DESC",
            columns=["CountryCodeTo", "UTCTime", "Quantity", "Unit", "Resolution"],
        )
        imp = _series_prioritize_pt60m(df_imp, "Quantity").to_frame("Imports")

        # --- Exports ---
        df_exp = db.query_table(
            "bigcloud_db",
            "dbo.EuropeInterconnectionActuals",
            filters={"CountryCodeFrom": country},
            order_by="UTCTime DESC",
            columns=["CountryCodeFrom", "UTCTime", "Quantity", "Unit", "Resolution"],
        )
        exp = _series_prioritize_pt60m(df_exp, "Quantity").to_frame("Exports")

        # --- Merge all, aligned to demand ---
        df = (
            dem.join(gen, how="left")
            .join(cap, how="left")
            .join(imp, how="left")
            .join(exp, how="left")
            .reindex(dem.index)  # exact alignment
            .sort_index()
        )

        return df




    

