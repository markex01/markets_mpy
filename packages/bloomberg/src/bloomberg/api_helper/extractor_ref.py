import pandas as pd
import numpy as np
import blpapi
import re
import datetime as dt
import warnings
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from typing import Optional, Tuple, Any

EXUS_COLORS = [
    "#004d4d", "#006666", "#008080", "#009999",
    "#00cccc", "#336666", "#00b3b3"
]
warnings.filterwarnings("always")

class BloombergExtractor:
    """Clase para extraer datos de Bloomberg con soporte de frecuencias H, D, W, M y Y."""
    def __init__(self, host: str = 'localhost', port: int = 8194):
        self.host = host
        self.port = port
        self.session = self._create_session()

    def _create_session(self):
        opts = blpapi.SessionOptions()
        opts.setServerHost(self.host)
        opts.setServerPort(self.port)
        session = blpapi.Session(opts)
        if not session.start():
            raise ConnectionError("No se pudo iniciar sesión Bloomberg")
        else:
            print("Sesión Bloomberg iniciada")
        if not session.openService("//blp/refdata"):
            raise ConnectionError("No se pudo abrir el servicio //blp/refdata")
        else:
            print("Servicio //blp/refdata abierto")
        if not session.openService("//blp/instruments"):
            raise ConnectionError("No se pudo abrir el servicio //blp/instruments")
        else:
            print("Servicio //blp/instruments abierto")
        return session

    def _get_historical(self,
                        securities: list[str],
                        field: str,
                        start_date: str,
                        end_date: str,
                        period_sel: str = "DAILY") -> pd.DataFrame:
        svc = self.session.getService("//blp/refdata")
        req = svc.createRequest("HistoricalDataRequest")
        for s in securities:
            req.getElement("securities").appendValue(s)
        req.getElement("fields").appendValue(field)
        req.set("startDate", start_date)
        req.set("endDate",   end_date)
        req.set("periodicityAdjustment", "ACTUAL")
        req.set("periodicitySelection",  period_sel)
        self.session.sendRequest(req)
        rows = []
        while True:
            ev = self.session.nextEvent()
            for msg in ev:
                if msg.messageType() == blpapi.Name("HistoricalDataResponse"):
                    sd = msg.getElement("securityData")
                    if sd.hasElement("securityError"):
                        continue
                    sec = sd.getElementAsString("security")
                    fd = sd.getElement("fieldData")
                    for i in range(fd.numValues()):
                        e = fd.getValueAsElement(i)
                        if not e.hasElement("date"): continue
                        dt = e.getElementAsDatetime("date")
                        val = e.getElementAsFloat(field) if e.hasElement(field) else None
                        rows.append({"_sec": sec, "Date": dt, "value": val})
            if ev.eventType() == blpapi.Event.RESPONSE:
                break
        return pd.DataFrame(rows)

    def _get_security_meta(self,
                        securities: list[str],
                        meta_fields: list[str] | None = None
                        ) -> dict[str, dict[str, Any]]:
        if meta_fields is None:
            meta_fields = ["CRNCY", "PX_UNIT"]

        svc = self.session.getService("//blp/refdata")
        req = svc.createRequest("ReferenceDataRequest")

        secs_el = req.getElement("securities")
        fields_el = req.getElement("fields")

        for s in securities:
            secs_el.appendValue(s)

        for f in meta_fields:
            fields_el.appendValue(f)

        self.session.sendRequest(req)

        out: dict[str, dict[str, Any]] = {}

        while True:
            ev = self.session.nextEvent()
            for msg in ev:
                if msg.messageType() != blpapi.Name("ReferenceDataResponse"):
                    continue

                sd_array = msg.getElement("securityData")
                for i in range(sd_array.numValues()):
                    sd = sd_array.getValueAsElement(i)
                    sec = sd.getElementAsString("security")

                    if sd.hasElement("securityError"):
                        # puedes loggear el error si quieres
                        continue

                    fd = sd.getElement("fieldData")
                    meta: dict[str, Any] = {}
                    for f in meta_fields:
                        if fd.hasElement(f):
                            meta[f] = fd.getElement(f).getValue()
                    out[sec] = meta

            if ev.eventType() == blpapi.Event.RESPONSE:
                break

        return out

    def get_security_currency(self, security: str
                          ) -> Tuple[Optional[str], Optional[str]]:

        meta = self._get_security_meta([security])  # usa CRNCY, PX_UNIT por defecto
        info = meta.get(security, {})
        crncy = info.get("CRNCY")
        unit = info.get("PX_UNIT")
        return crncy, unit

    def get_hourly_prices(self, prefix: str, start_date: str, end_date: str, field_name: str = 'PX_LAST') -> pd.DataFrame:
        ticks = [f"{prefix}{h:02d} Index" for h in range(1, 26)]
        df = self._get_historical(ticks, field_name, start_date, end_date)
        if df.empty:
            return df
        df[['Hour']] = df['_sec'].str.extract(r"(\d{2}) Index").astype(int)
        df = df[['Date', 'Hour', 'value']].rename(columns={'value': 'Price'})
        df = df.sort_values(['Date', 'Hour']).reset_index(drop=True)
        df['Date'] = df['Date'] + pd.Timedelta(days=1)
        return df

    def remap_dst_hours(self, df: pd.DataFrame) -> pd.DataFrame:
        def transform(sub: pd.DataFrame, day):
            hrs = sub['Hour'].unique()
            s = sub.copy()
            if 25 in hrs:
                s['Hour'] = s['Hour'].apply(lambda h: h if h <= 3 else (4 if h == 25 else h + 1))
            elif 3 not in hrs:
                s['Hour'] = s['Hour'].apply(lambda h: h if h <= 2 else h - 1)
            s['Date'] = day
            return s
        out = df.groupby('Date', group_keys=False).apply(lambda g: transform(g[['Hour','Price']], g.name))
        return out[['Date', 'Hour', 'Price']].sort_values(['Date', 'Hour']).reset_index(drop=True)

    def get_dam_prices(self, markets: list[tuple[str, str]], start_date: str, end_date: str, freq: str = 'H') -> pd.DataFrame:
        dfs = []
        for prefix, name in markets:
            df = self.get_hourly_prices(prefix, start_date, end_date)
            if df.empty:
                dfs.append(pd.DataFrame(columns=['Date', 'Hour', name]))
            else:
                df = self.remap_dst_hours(df)
                df = df.rename(columns={'Price': name})
                dfs.append(df)
        if not dfs:
            return pd.DataFrame()
        merged = dfs[0]
        for df in dfs[1:]:
            merged = merged.merge(df, on=['Date', 'Hour'], how='outer')
        merged = merged.sort_values(['Date', 'Hour']).reset_index(drop=True)
        return self._apply_freq(merged, freq)

    def extraction_prices(self, countries: list[str], startdate: str, enddate: str, freq: str = 'H') -> pd.DataFrame:
        valid = {'UK':'N2EXH','ES':'OMLPHR','IT':'GMEPIT','PL':'PXPEDA','IR':'SEMODE','GE':'LPXBHR','FR':'PWNXFR'}
        codes = sorted(valid.keys())
        invalid = [c for c in countries if c not in valid]
        if invalid:
            for c in invalid:
                print(f"{c} no es un código aceptado.")
            print(f"La lista de códigos aceptados es: {codes}")
        markets = [(valid[c], c) for c in countries if c in valid]
        if not markets:
            print("No se cargaron mercados válidos. Verifica los códigos.")
            return pd.DataFrame()
        return self.get_dam_prices(markets, startdate, enddate, freq)

    def extraction_ticker(self,
                          name: str,
                          ticker: str,
                          field: str,
                          startdate: str,
                          enddate: str,
                          freq: str = 'D') -> pd.DataFrame:
        # mapeo interno a las opciones de Bloomberg
        freq_map = {
            'H': "DAILY",    # no hay “hourly” en API, así que usas RAW hourly y luego…
            'D': "DAILY",
            'W': "WEEKLY",
            'M': "MONTHLY",
            'Q': "QUARTERLY",
            'Y': "YEARLY",
        }
        period_sel = freq_map[freq.upper()]
        # para H igual sigues tirando de _get_historical de hora en hora
        df = self._get_historical([ticker], field, startdate, enddate, period_sel)
        if df.empty:
            return df
        # en el caso de D/W/M/Y la API ya te entrega el dato agregado
        df = df[['Date','value']].rename(columns={'value': name})
        # si quieres homogeneizar nombres de columna:
        if freq.upper() == 'M':
            df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%d/%m/%Y')
        elif freq.upper() == 'Y':
            df['Date'] = pd.to_datetime(df['Date']).dt.year
        # para Weekly podría pasar a date sólo:
        elif freq.upper() == 'W':
            df['Date'] = pd.to_datetime(df['Date']).dt.date
        elif freq.upper() == 'Q':
            df['Date'] = pd.to_datetime(df['Date']).dt.to_period('Q').astype(str)
        return df

    def _apply_freq(self, df: pd.DataFrame, freq: str) -> pd.DataFrame:
        df = df.copy()
        df['Date'] = pd.to_datetime(df['Date'])
        code = freq.upper()
        if code not in ['H','D','W','M','Y']:
            raise ValueError(f"Frecuencia desconocida: {freq}. Use H, D, W, M o Y.")
        if code == 'H':
            return df
        rule = {'D':'D','W':'W','M':'M','Y':'A'}[code]
        if 'Hour' in df.columns:
            df = df.drop(columns='Hour')
        df = df.set_index('Date').resample(rule).mean().reset_index()
        if code == 'D':
            df = df.rename(columns={'Date':'Day'})
        elif code == 'W':
            df['Date'] = df['Date'].dt.date
        elif code == 'M':
            df['Date'] = df['Date'].dt.strftime('%d/%m/%Y')
        else:
            df['Date'] = df['Date'].dt.year
        return df

    def search_securities(self,
                          query: str,
                          max_results: int = 20,
                          yellow_key_filter: str | None = None,
                          language_override: str = "LANG_OVERRIDE_NONE"
                          ) -> pd.DataFrame:
        # --- InstrumentListRequest ---
        svc = self.session.getService("//blp/instruments")
        req = svc.createRequest("instrumentListRequest")
        req.set("query", query)
        req.set("maxResults", max_results)
        req.set("languageOverride", language_override)
        if yellow_key_filter:
            req.set("yellowKeyFilter", yellow_key_filter)

        self.session.sendRequest(req)

        rows = []
        while True:
            ev = self.session.nextEvent()
            for msg in ev:
                if msg.hasElement("responseError"):
                    raise RuntimeError(
                        msg.getElement("responseError")
                           .getElementAsString("message")
                    )

                if msg.messageType() == blpapi.Name("InstrumentListResponse"):
                    for res in msg.getElement("results").values():
                        sec  = res.getElementAsString("security")
                        desc = res.getElementAsString("description")
                        # extrae texto entre < >
                        m = re.search(r"<([^>]+)>", sec)
                        a_type = m.group(1).lower() if m else None
                        rows.append({
                            "Asset_type":  a_type,   # p. ej. equity, corp, cds…
                            "Security":    sec,
                            "Description": desc
                        })
            if ev.eventType() == blpapi.Event.RESPONSE:
                break

        # orden final de columnas y limpieza
        df = pd.DataFrame(rows)[["Asset_type", "Security", "Description"]]
        return df

    # ──────────────────────────────────────────────────────────────
    def list_ecfc_core(self,
                    country: str,
                    include_quarterly: bool = False,
                    max_results: int = 500,
                    language_override: str = "LANG_OVERRIDE_NONE") -> pd.DataFrame:

        svc = self.session.getService("//blp/instruments")
        req = svc.createRequest("instrumentListRequest")
        req.set("query", f"ECFC {country}")
        req.set("maxResults", max_results)
        req.set("languageOverride", language_override)
        self.session.sendRequest(req)

        rows = []
        while True:
            ev = self.session.nextEvent()
            for msg in ev:
                if msg.messageType() == blpapi.Name("InstrumentListResponse"):
                    for res in msg.getElement("results").values():
                        rows.append({
                            "security":    res.getElementAsString("security"),
                            "description": res.getElementAsString("description")
                        })
            if ev.eventType() == blpapi.Event.RESPONSE:
                break
        df = pd.DataFrame(rows)

        #––– FILTER ––––––––––––––––––––––––––––––––––––––––––
        df = df[~df['description'].str.contains(r'\b(High|Low|Average)\b', case=False, na=False)]
        if not include_quarterly:
            df = df[~df['description'].str.contains(r'\bQ\d',  regex=True, na=False)]
        df = df[~df['description'].str.startswith("  ", na=False)]   # dos espacios = sub‑fila
        return df.drop_duplicates(subset='description', keep='first').reset_index(drop=True)

    # ──────────────────────────────────────────────────────────────
    def ecfc_annual_table(self,
                                country: str,
                                last_years: int = 7,
                                forward_years: int = 6):
        
    # ecfc

        # --- suffix map -------------------------------------------------
        ctry_suffix = {
            'Eurozone': 'EU', 'EZ': 'EU', 'EU': 'EU',
            'United States': 'US', 'US': 'US',
            'European Union': 'EUN', 'EUN': 'EUN',
            'Western Europe': 'WE', 'WE': 'WE',
            'Spain': 'ES', 'ES': 'ES',
            'France': 'FR', 'FR': 'FR',
            'Italy' : 'IT', 'IT': 'IT',
            'Germany': 'DE', 'DE': 'DE',
            'Poland' : 'PL', 'PL': 'PL',
            'United Kingdom': 'UK', 'UK': 'UK',
            'Ireland': 'IE', 'IE': 'IE',
        }
        if country not in ctry_suffix:
            raise ValueError(f"No suffix mapping for '{country}'")
        suffix = ctry_suffix[country]

        # --- 1) catalogue (annual rows) ---------------------------------
        cat = self.list_ecfc_core(country,
                                  include_quarterly=False,
                                  max_results=800)

        country_lc = country.lower()
        originals = cat[
            (cat['security'].str.startswith('EH')) &
            (~cat['description'].str.contains('Forecast', case=False, na=False)) &
            (cat['description'].str.lower().str.startswith(country_lc))
        ]
        if originals.empty:
            raise RuntimeError(f"No EH originals found for '{country}'.")

        today      = dt.date.today()
        today_str  = today.strftime("%Y%m%d")
        start_str  = today.replace(year=today.year - 10).strftime("%Y%m%d")

        def tidy(tkr: str) -> str:
            t = re.sub(r'<[^>]+>', '', tkr).strip()
            return t if t.lower().endswith(' index') else t + ' Index'

        table_rows, pair_rows = [], []

        # --- 2) iterate originals --------------------------------------
        for _, row in originals.iterrows():
            eh_raw = row.security
            eh_tkr = tidy(eh_raw)
            descr  = row.description.strip()

            # central code: remove EH, <index>, final letter(s) until suffix
            code = re.sub(r'^EH', '', eh_raw)
            code = re.sub(r'<.*', '', code)
            while len(code) > len(suffix) and not code.endswith(suffix):
                code = code[:-1]
            if not code.endswith(suffix):
                continue  # not the requested region

            fc_code = code
            if suffix == 'EUN':
                fc_code = code[:-3] + 'E2'

            # print(f"\n▶ {descr}")
            # print(f"  EH : {eh_tkr}")

             # ----- historical ------------------------------------------
            hist = self.extraction_ticker("HIST", eh_tkr, "PX_LAST",
                                          start_str, today_str, freq='Y')
            if not hist.empty:
                num_col = [c for c in hist.columns
                           if hist[c].dtype in (np.float64, np.int64)][0]
                for _, h in hist.tail(last_years).iterrows():
                    yr = str(int(h['Date']))
                    table_rows.append([descr, yr, h[num_col]])

            # ----- forecasts -------------------------------------------
            for yr in range(today.year, today.year + forward_years):
                fc_tkr = tidy(f"EC{fc_code} {str(yr)[2:]} Index")
                print(fc_tkr)
                fc_df  = self.extraction_ticker("FC", fc_tkr, "PX_LAST",
                                                start_str, today_str, freq='D')
                if fc_df.empty:
                    continue
                val = fc_df.iloc[-1, 1]
                # print(f"    ✔ {fc_tkr}  →  {yr} = {val}")
                table_rows.append([descr, str(yr), val])
                pair_rows.append([descr, fc_tkr, str(yr), val])

        if not table_rows:
            raise RuntimeError("No data retrieved (check Bloomberg access).")

        # --- 3) build outputs ------------------------------------------
        df = pd.DataFrame(table_rows,
                          columns=['Indicator', 'Year', 'Value'])
        table_df = (df.pivot_table(index='Indicator',
                                   columns='Year',
                                   values='Value',
                                   aggfunc='last')
                      .sort_index(axis=1))

        pairs_df = pd.DataFrame(pair_rows,
                                columns=['Original', 'Forecast', 'Year', 'Value'])

        return table_df

    # ──────────────────────────────────────────────────────────────
    def ecfc_quarterly_table(self,
                                   country: str,
                                   last_quarters: int = 8,
                                   forward_quarters: int = 12):

        # --- suffix map -------------------------------------------------
        ctry_suffix = {
            'Eurozone': 'EU', 'EZ': 'EU', 'EU': 'EU',
            'European Union': 'EUN', 'EUN': 'EUN',
            'Western Europe': 'WE', 'WE': 'WE',
            'Spain': 'ES', 'ES': 'ES',
            'France': 'FR', 'FR': 'FR',
            'Italy': 'IT', 'IT': 'IT',
            'Germany': 'DE', 'DE': 'DE',
            'Poland': 'PL', 'PL': 'PL',
            'United Kingdom': 'UK', 'UK': 'UK',
            'Ireland': 'IE', 'IE': 'IE',
        }
        if country not in ctry_suffix:
            raise ValueError(f"No suffix mapping for '{country}'")
        suffix = ctry_suffix[country]

        # --- 1) catalogue ---------------------------------------------
        cat = self.list_ecfc_core(country,
                                  include_quarterly=True,
                                  max_results=800)

        originals = cat[
            (cat['security'].str.startswith('EH')) &
            (~cat['description'].str.contains('Forecast', case=False, na=False)) &
            (cat['description'].str.lower().str.startswith(country.lower()))
        ]
        if originals.empty:
            raise RuntimeError(f"No EH originals found for '{country}'.")

        today      = dt.date.today()
        today_str  = today.strftime("%Y%m%d")
        start_str  = today.replace(year=today.year - 2).strftime("%Y%m%d")

        def tidy(t: str) -> str:
            t = re.sub(r'<[^>]+>', '', t).strip()
            return t if t.lower().endswith(' index') else t + ' Index'

        rows, pairs = [], []

        # --- 2) iterate indicators ------------------------------------
        for _, row in originals.iterrows():
            eh_raw = row.security
            eh_tkr = tidy(eh_raw)
            descr  = row.description.strip()

            # derive core code
            code = re.sub(r'^EH', '', eh_raw)
            code = re.sub(r'<.*', '', code)
            while len(code) > len(suffix) and not code.endswith(suffix):
                code = code[:-1]
            if not code.endswith(suffix):
                continue

            fc_code = code[:-3] + 'E2' if suffix == 'EUN' else code


            # ----- historical (freq='Q') ------------------------------
            hist = self.extraction_ticker("HIST", eh_tkr, "PX_LAST",
                                          start_str, today_str, freq="Q")
            if not hist.empty:
                vcol = [c for c in hist.columns
                        if hist[c].dtype.kind in ('f', 'i')][0]
                hist = hist.tail(last_quarters)
                for _, h in hist.iterrows():
                    q_raw = str(h['Quarter'])          # e.g. '2025Q1'
                    m = re.match(r'(\d{4})Q([1-4])', q_raw)
                    q_lab = f"Q{m.group(2)} {m.group(1)}" if m else q_raw
                    rows.append([descr, q_lab, h[vcol]])

            # ----- forecasts -----------------------------------------
            q_seq = pd.period_range(start=today,
                                    periods=forward_quarters,
                                    freq='Q')
            for per in q_seq:
                qyy = f"Q{per.quarter}{str(per.year)[2:]}"
                fc_tkr = tidy(f"EC{fc_code} {qyy} Index")
                fc_df  = self.extraction_ticker("FC", fc_tkr, "PX_LAST",
                                                start_str, today_str, freq='D')
                if fc_df.empty:
                    continue
                val   = fc_df.iloc[-1, 1]
                q_lab = f"Q{per.quarter} {per.year}"
                # print(f"    ✔ {fc_tkr}  →  {q_lab} = {val}")
                rows.append([descr, q_lab, val])
                pairs.append([descr, fc_tkr, q_lab, val])

        if not rows:
            raise RuntimeError("No data retrieved – verify Bloomberg access.")

        # --- 3) build outputs ----------------------------------------
        df = pd.DataFrame(rows,
                          columns=['Indicator', 'Quarter', 'Value'])
        table = (df.pivot_table(index='Indicator',
                                columns='Quarter',
                                values='Value',
                                aggfunc='last'))

        # proper chronological order
        def q_key(label: str):
            m = re.match(r'Q([1-4])\s+(\d{4})', label)
            m2 = re.match(r'(\d{4})Q([1-4])', label)
            if m:
                return int(m.group(2)), int(m.group(1))
            if m2:
                return int(m2.group(1)), int(m2.group(2))
            return (9999, 9)
        table = table.reindex(sorted(table.columns, key=q_key), axis=1)

        pairs_df = pd.DataFrame(pairs,
                                columns=['Original', 'Forecast', 'Quarter', 'Value'])

        return table

    # ──────────────────────────────────────────────────────────────
    def list_cpfc_core(self,
                    category: str,
                    ticker_type: str = "Generic",
                    max_results: int = 500,
                    language_override: str = "LANG_OVERRIDE_NONE") -> pd.DataFrame:

        svc = self.session.getService("//blp/instruments")
        req = svc.createRequest("instrumentListRequest")
        # La cadena de búsqueda funciona muy bien con “CPFC <Category> <TickerType>”
        req.set("query", f"CPFC {category} {ticker_type}")
        req.set("maxResults", max_results)
        req.set("languageOverride", language_override)
        self.session.sendRequest(req)

        rows = []
        while True:
            ev = self.session.nextEvent()
            for msg in ev:
                if msg.messageType() == blpapi.Name("InstrumentListResponse"):
                    for res in msg.getElement("results").values():
                        rows.append({
                            "security":    res.getElementAsString("security"),
                            "description": res.getElementAsString("description")
                        })
            if ev.eventType() == blpapi.Event.RESPONSE:
                break

        # las sub‑filas (sangradas) no nos interesan
        out = (pd.DataFrame(rows)
                .query("~description.str.startswith('  ')",
                        engine='python')
                .drop_duplicates("description")
                .reset_index(drop=True))
        return out
    
    def plot_energy_prices(self,
        countries: list[str],start: str,end: str,
        freq: str = "D",title: str = "Energy Prices",ylabel: str = "€/MWh",
        secondary: list[str] | None = None
    ):
        df = self.extraction_prices(countries, start, end, freq=freq)
        df["Day"] = pd.to_datetime(df["Day"])
        df = df.set_index("Day").astype(float)

        self._plot_generic(
            df,
            title,
            ylabel,
            secondary=secondary or []
        )

    def plot_ticker_series(self,
        tickers: dict[str,str],start: str,end: str,
        freq: str = "D",db: str = "PRICE",field: str = "PX_LAST",
        title: str = "",ylabel: str = "",
        secondary: list[str] | None = None,
        overlay: dict[str,str] | None = None
    ):
        frames = []
        for label, tkr in tickers.items():
            df0 = self.extraction_ticker(db, tkr, field, start, end, freq=freq)
            for c in df0.columns:
                dt = pd.to_datetime(df0[c], errors="coerce")
                if dt.notna().mean() > 0.8:
                    df0 = df0.set_index(dt).drop(columns=[c])
                    break
            s = pd.to_numeric(df0.iloc[:,0], errors="coerce").rename(label)
            frames.append(s)
        df = pd.concat(frames, axis=1)

        if overlay:
            ov_frames = []
            for label, tkr in overlay.items():
                df0 = self.extraction_ticker(db, tkr, field, start, end, freq=freq)
                for c in df0.columns:
                    dt = pd.to_datetime(df0[c], errors="coerce")
                    if dt.notna().mean() > 0.8:
                        df0 = df0.set_index(dt).drop(columns=[c])
                        break
                s = pd.to_numeric(df0.iloc[:,0], errors="coerce").rename(label)
                ov_frames.append(s)
            df = pd.concat([df] + ov_frames, axis=1)

        self._plot_generic(df, title, ylabel, secondary=secondary or [])

    def _plot_generic(
        self,
        df: pd.DataFrame,
        title: str,
        ylabel: str,
        secondary: list[str]
    ):
        fig, ax = plt.subplots(figsize=(12,6))
        ax2 = ax.twinx() if secondary else None
        
        for i, col in enumerate(df.columns):
            target = ax2 if ax2 and col in secondary else ax
            style = "--" if target is ax2 else "-"
            target.plot(
                df.index, df[col],
                label=col,
                color=EXUS_COLORS[i % len(EXUS_COLORS)],
                linewidth=1.8,
                linestyle=style
            )
        
        ax.set_title(title, loc="left", fontsize=14, weight="bold")
        ax.set_ylabel(ylabel)
        if ax2:
            ax2.set_ylabel(ylabel + " (sec.)")
        ax.grid(alpha=0.3, linestyle="--")
        
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
        fig.autofmt_xdate()
        
        h, l = ax.get_legend_handles_labels()
        if ax2:
            h2, l2 = ax2.get_legend_handles_labels()
            h, l = h+h2, l+l2
        ax.legend(h, l, frameon=False, ncol=2, title="Serie")
        plt.tight_layout()
        plt.show()

    def build_financial_dataset(self, start: str, end: str, field: str = "PX_LAST", freq: str = "D",
                                out_xlsx: str | None = "financial_data.xlsx",
                                include_components_sheet: bool = False):

        import pandas as pd
        import datetime as dt
        from pandas.tseries.offsets import MonthEnd

        # ---------------- Helpers ----------------
        def _looks_monthly(date_series: pd.Series) -> bool:
            d = pd.to_datetime(date_series)
            if d.empty: return False
            if not (d == (d + MonthEnd(0))).all(): return False
            by_month = pd.Series(1, index=d).groupby([d.dt.year, d.dt.month]).sum()
            return (by_month <= 1).all()

        def _normalize(df: pd.DataFrame, target_col: str) -> pd.DataFrame:
            if df is None or df.empty:
                return pd.DataFrame(columns=["Date", target_col])
            if "Date" not in df.columns:
                df = df.rename(columns={df.columns[0]: "Date"})
            df["Date"] = pd.to_datetime(df["Date"])
            if target_col not in df.columns:
                df = df.rename(columns={df.columns[-1]: target_col})
            df = df.sort_values("Date").drop_duplicates(subset="Date", keep="last")
            return df[["Date", target_col]]

        def _pull_simple(name: str, ticker: str) -> pd.DataFrame:
            raw = self.extraction_ticker(name, ticker, field, start, end, freq=freq)
            return _normalize(raw, name)

        def _merge_keep_current(name: str, df_legacy: pd.DataFrame, df_current: pd.DataFrame) -> pd.DataFrame:
            if not df_legacy.empty and df_legacy.columns[-1] != name + "_legacy":
                df_legacy = df_legacy.rename(columns={df_legacy.columns[-1]: name + "_legacy"})
            if not df_current.empty and df_current.columns[-1] != name + "_current":
                df_current = df_current.rename(columns={df_current.columns[-1]: name + "_current"})
            dm = pd.merge(df_legacy, df_current, on="Date", how="outer").sort_values("Date")
            if name + "_current" in dm.columns and name + "_legacy" in dm.columns:
                dm[name] = dm[name + "_current"].combine_first(dm[name + "_legacy"])
            elif name + "_current" in dm.columns:
                dm[name] = dm[name + "_current"]
            else:
                dm[name] = dm[name + "_legacy"]
            return dm[["Date", name]]

        # -------------- Ticker maps --------------
        # EUR OIS
        ois_tickers = {
            "1W":"EESWE1Z BGN Curncy","1M":"EESWEA BGN Curncy","3M":"EESWEC BGN Curncy",
            "6M":"EESWEF BGN Curncy","1Y":"EESWE1 BGN Curncy","2Y":"EESWE2 BGN Curncy",
            "3Y":"EESWE3 BGN Curncy","5Y":"EESWE5 BGN Curncy","7Y":"EESWE7 BGN Curncy",
            "10Y":"EESWE10 BGN Curncy","15Y":"EESWE15 BGN Curncy","20Y":"EESWE20 BGN Curncy",
            "30Y":"EESWE30 BGN Curncy","40Y":"EESWE40 BGN Curncy","50Y":"EESWE50 BGN Curncy"
        }
        # EUR 6M swaps
        eur6m_tickers = {
            "6M":"EUR006M Index","1Y":"EUFR0F1 BGN Curncy","2Y":"EUSA2 BGN Curncy",
            "3Y":"EUSA3 BGN Curncy","4Y":"EUSA4 BGN Curncy","5Y":"EUSA5 BGN Curncy",
            "7Y":"EUSA7 BGN Curncy","10Y":"EUSA10 BGN Curncy","12Y":"EUSA12 BGN Curncy",
            "15Y":"EUSA15 BGN Curncy","20Y":"EUSA20 BGN Curncy","25Y":"EUSA25 BGN Curncy",
            "30Y":"EUSA30 BGN Curncy","40Y":"EUSA40 BGN Curncy","50Y":"EUSA50 BGN Curncy"
        }

        # USD OIS / Swaps / GBP OIS / PLN OIS & SWAPS
        usd_ois = {
            "1D":"FEDL01 Index","1W":"USSO1Z BGN Curncy","2W":"USSO2Z BGN Curncy","1M":"USSOA BGN Curncy",
            "2M":"USSOB BGN Curncy","3M":"USSOC BGN Curncy","6M":"USSOF BGN Curncy","9M":"USSOI BGN Curncy",
            "1Y":"USSO1 BGN Curncy","2Y":"USSO2 BGN Curncy","3Y":"USSO3 BGN Curncy","5Y":"USSO5 BGN Curncy",
            "7Y":"USSO7 BGN Curncy","10Y":"USSO10 BGN Curncy","15Y":"USSO15 BGN Curncy","20Y":"USSO20 BGN Curncy",
            "30Y":"USSO30 BGN Curncy","40Y":"USSO40 BGN Curncy"
        }
        usd_swaps = {
            "1D":"SOFRRATE Index","1W":"USOSFR1Z BGN Curncy","1M":"USOSFRA BGN Curncy","3M":"USOSFRC BGN Curncy",
            "6M":"USOSFRF BGN Curncy","1Y":"USOSFR1 BGN Curncy","2Y":"USOSFR2 BGN Curncy","3Y":"USOSFR3 BGN Curncy",
            "5Y":"USOSFR5 BGN Curncy","7Y":"USOSFR7 BGN Curncy","10Y":"USOSFR10 BGN Curncy","15Y":"USOSFR15 BGN Curncy",
            "20Y":"USOSFR20 BGN Curncy","30Y":"USOSFR30 BGN Curncy","40Y":"USOSFR40 BGN Curncy","50Y":"USOSFR50 BGN Curncy"
        }
        gbp_ois = {
            "1D":"SONIO/N Index","1W":"BPSWS1Z BGN Curncy","1M":"BPSWSA BGN Curncy","3M":"BPSWSC BGN Curncy",
            "6M":"BPSWSF BGN Curncy","1Y":"BPSWS1 BGN Curncy","2Y":"BPSWS2 BGN Curncy","3Y":"BPSWS3 BGN Curncy",
            "5Y":"BPSWS5 BGN Curncy","7Y":"BPSWS7 BGN Curncy","10Y":"BPSWS10 BGN Curncy","15Y":"BPSWS15 BGN Curncy",
            "20Y":"BPSWS20 BGN Curncy","30Y":"BPSWS30 BGN Curncy","40Y":"BPSWS40 BGN Curncy","50Y":"BPSWS50 BGN Curncy"
        }

        pln_wibor6m = {
            "6M":"WIBR6M Index","7M":"PZFR0AG CMPN Curncy","8M":"PZFR0BH CMPN Curncy","9M":"PZFR0CI CMPN Curncy",
            "10M":"PZFR0DJ CMPN Curncy","11M":"PZFR0EK CMPN Curncy","12M":"PZFR0F1 CMPN Curncy",
            "18M":"PZFR011F CMPN Curncy","2Y":"PZSW2 BGN Curncy","3Y":"PZSW3 BGN Curncy","4Y":"PZSW4 BGN Curncy",
            "5Y":"PZSW5 BGN Curncy","6Y":"PZSW6 BGN Curncy","7Y":"PZSW7 BGN Curncy","8Y":"PZSW8 BGN Curncy",
            "9Y":"PZSW9 BGN Curncy","10Y":"PZSW10 BGN Curncy","12Y":"PZSW12 BGN Curncy"
        }
        pln_ois = {
            "1D":"PZCFPLNI Index","1Y":"PZSO1 CMPN Curncy","2Y":"PZSO2 CMPN Curncy","3Y":"PZSO3 CMPN Curncy",
            "4Y":"PZSO4 CMPN Curncy","5Y":"PZSO5 CMPN Curncy","6Y":"PZSO6 CMPN Curncy","7Y":"PZSO7 CMPN Curncy",
            "8Y":"PZSO8 CMPN Curncy","9Y":"PZSO9 CMPN Curncy","10Y":"PZSO10 CMPN Curncy"
        }

        # EUR 6M basis (1M vs 6M, 3M vs 6M)
        basis_tenors = ["1Y","2Y","3Y","5Y","7Y","10Y","15Y","20Y","30Y"]
        # basis_1m_6m = {f"Basis_1Mvs6M_{t}": f"EUSW{t.replace('Y','')}V1 Curncy" for t in basis_tenors}
        basis_3m_6m = {f"Basis_3Mvs6M_{t}": f"EUBSV{t.replace('Y','')} Curncy"  for t in basis_tenors}

        # Inflation
        euro_inflation = {"ZCIS": {f"{n}Y": f"EUSWI{n} Curncy" for n in [10]},
                          "YoY": "CPTFEMUY Index"}
        usa_inflation  = {"ZCIS": {f"{n}Y": f"USSWIT{n} Curncy" for n in [10]},
                          "YoY": "CPI YOY Index"}
        uk_inflation   = {"ZCIS": {f"{n}Y": f"BPSWIT{n} Curncy" for n in [10]},
                          "YoY": "UKRPYOY Index"}
        current_year = dt.date.today().year
        pln_inflation = {"Forecasts": {str(y): f"ECPIPL {str(y)[-2:]} Index" for y in range(current_year, current_year+3)},
                         "YoY": "POCPIYOY Index"}

        # FX spot
        fx_spot = {"EURUSD": "EURUSD Curncy", "GBPUSD": "GBPUSD Curncy", "EURPLN": "EURPLN Curncy"}

        # EURPLN basis
        eurpln_basis = {
            # "1M":"EURPLN1M CMPN Curncy","2M":"EURPLN2M CMPN Curncy","3M":"EURPLN3M CMPN Curncy",
            # "4M":"EURPLN4M CMPN Curncy","5M":"EURPLN5M CMPN Curncy","6M":"EURPLN6M CMPN Curncy",
            # "9M":"EURPLN9M CMPN Curncy","12M":"PZEU12M CMPN Curncy",
            "2Y":"PZBSEC2 CMPN Curncy","5Y":"PZBSEC5 CMPN Curncy", "10Y":"PZBSEC10 CMPN Curncy",
            # "3Y":"PZBSEC3 CMPN Curncy","4Y":"PZBSEC4 CMPN Curncy",
            # "7Y":"PZBSEC7 CMPN Curncy",,"12Y":"PZBSEC12 CMPN Curncy"
        }

        # EURUSD/GBPUSD basis (legacy & current) for merged series
        eurusd_legacy = {
            #"1Y":"EUBS1 Curncy","2Y":"EUBS2 Curncy","3Y":"EUBS3 Curncy","4Y":"EUBS4 Curncy","5Y":"EUBS5 Curncy",
            #"6Y":"EUBS6 Curncy","7Y":"EUBS7 Curncy","8Y":"EUBS8 Curncy","9Y":"EUBS9 Curncy","10Y":"EUBS10 Curncy",
            #"12Y":"EUBS12 Curncy","15Y":"EUBS15 Curncy","20Y":"EUBS20 Curncy","25Y":"EUBS25 Curncy","30Y":"EUBS30 Curncy"
            "2Y":"EUBS2 Curncy", "5Y":"EUBS5 Curncy", "10Y":"EUBS10 Curncy"
        }
        eurusd_current = {
            #"2Y":"EUXOQQ2 BGN Curncy","3Y":"EUXOQQ3 BGN Curncy","4Y":"EUXOQQ4 BGN Curncy","5Y":"EUXOQQ5 BGN Curncy",
            #"6Y":"EUXOQQ6 BGN Curncy","7Y":"EUXOQQ7 BGN Curncy","8Y":"EUXOQQ8 BGN Curncy","9Y":"EUXOQQ9 BGN Curncy",
            #"10Y":"EUXOQQ10 BGN Curncy","12Y":"EUXOQQ12 BGN Curncy","15Y":"EUXOQQ15 BGN Curncy",
            #"20Y":"EUXOQQ20 BGN Curncy","30Y":"EUXOQQ30 BGN Curncy"
            "2Y":"EUXOQQ2 BGN Curncy", "5Y":"EUXOQQ5 BGN Curncy", "10Y":"EUXOQQ10 BGN Curncy"
        }

        gbpusd_legacy = {
            #"2Y":"BPBS2 Curncy","3Y":"BPBS3 Curncy","4Y":"BPBS4 Curncy","5Y":"BPBS5 Curncy","6Y":"BPBS6 Curncy",
            #"7Y":"BPBS7 Curncy","8Y":"BPBS8 Curncy","9Y":"BPBS9 Curncy","10Y":"BPBS10 Curncy","12Y":"BPBS12 Curncy",
            #"15Y":"BPBS15 Curncy","20Y":"BPBS20 Curncy","25Y":"BPBS25 Curncy","30Y":"BPBS30 Curncy"
            "2Y":"BPBS2 Curncy", "5Y":"BPBS5 Curncy", "10Y":"BPBS10 Curncy"
        }

        gbpusd_current = {
            #"2Y":"BPXOQQ2 BGN Curncy","3Y":"BPXOQQ3 BGN Curncy","4Y":"BPXOQQ4 BGN Curncy","5Y":"BPXOQQ5 BGN Curncy",
            #"6Y":"BPXOQQ6 BGN Curncy","7Y":"BPXOQQ7 BGN Curncy","8Y":"BPXOQQ8 BGN Curncy","9Y":"BPXOQQ9 BGN Curncy",
            #"10Y":"BPXOQQ10 BGN Curncy","12Y":"BPXOQQ12 BGN Curncy","15Y":"BPXOQQ15 BGN Curncy",
            #"20Y":"BPXOQQ20 BGN Curncy","30Y":"BPXOQQ30 BGN Curncy"
            "2Y":"BPXOQQ2 BGN Curncy", "5Y":"BPXOQQ5 BGN Curncy", "10Y":"BPXOQQ10 BGN Curncy"
        }

        _ten_sort = lambda x: (int(x[:-1]), x[-1])
        eurusd_tenors = sorted(set(eurusd_legacy) | set(eurusd_current), key=_ten_sort)
        gbpusd_tenors = sorted(set(gbpusd_legacy) | set(gbpusd_current), key=_ten_sort)

        # -------------- Downloads --------------
        dfs = []
        freq_hint = {}

        # EUR OIS
        for k, v in ois_tickers.items():
            nm = f"ois_{k}"; df = _pull_simple(nm, v)
            if not df.empty: freq_hint[nm] = "D" if not _looks_monthly(df["Date"]) else "M"; dfs.append(df)

        # EUR 6M swaps
        for k, v in eur6m_tickers.items():
            nm = f"eur6m_{k}"; df = _pull_simple(nm, v)
            if not df.empty: freq_hint[nm] = "D"; dfs.append(df)

        # USD OIS / USD swaps / GBP OIS
        for k, v in usd_ois.items():
            nm = f"usd_ois_{k}"; df = _pull_simple(nm, v)
            if not df.empty: freq_hint[nm] = "D"; dfs.append(df)
        for k, v in usd_swaps.items():
            nm = f"usd_swaps_{k}"; df = _pull_simple(nm, v)
            if not df.empty: freq_hint[nm] = "D"; dfs.append(df)
        for k, v in gbp_ois.items():
            nm = f"gbp_ois_{k}"; df = _pull_simple(nm, v)
            if not df.empty: freq_hint[nm] = "D"; dfs.append(df)

        # PLN WIBOR 6M strip
        for k, v in pln_wibor6m.items():
            nm = f"pln_wibor6m_{k}"; df = _pull_simple(nm, v)
            if not df.empty: freq_hint[nm] = "D"; dfs.append(df)

        # PLN OIS
        for k, v in pln_ois.items():
            nm = f"pln_ois_{k}"; df = _pull_simple(nm, v)
            if not df.empty: freq_hint[nm] = "D"; dfs.append(df)

        # EUR 6M basis 1M/3M vs 6M
        # for k, v in {**basis_1m_6m, **basis_3m_6m}.items():
        for k, v in {**basis_3m_6m}.items():

            nm = f"basis_{k}"; df = _pull_simple(nm, v)
            if not df.empty: freq_hint[nm] = "D"; dfs.append(df)
            
        # Inflation (EZ/US/UK/PLN)
        for k, v in euro_inflation["ZCIS"].items():
            nm = f"euro_inflation_ZCIS_{k}"; df = _pull_simple(nm, v)
            if not df.empty: freq_hint[nm] = "M" if _looks_monthly(df["Date"]) else "D"; dfs.append(df)
        df = _pull_simple("euro_inflation_YoY", euro_inflation["YoY"])
        if not df.empty: freq_hint["euro_inflation_YoY"] = "M" if _looks_monthly(df["Date"]) else "D"; dfs.append(df)

        for k, v in usa_inflation["ZCIS"].items():
            nm = f"usa_inflation_ZCIS_{k}"; df = _pull_simple(nm, v)
            if not df.empty: freq_hint[nm] = "M" if _looks_monthly(df["Date"]) else "D"; dfs.append(df)
        df = _pull_simple("usa_inflation_YoY", usa_inflation["YoY"])
        if not df.empty: freq_hint["usa_inflation_YoY"] = "M" if _looks_monthly(df["Date"]) else "D"; dfs.append(df)

        for k, v in uk_inflation["ZCIS"].items():
            nm = f"uk_inflation_ZCIS_{k}"; df = _pull_simple(nm, v)
            if not df.empty: freq_hint[nm] = "M" if _looks_monthly(df["Date"]) else "D"; dfs.append(df)
        df = _pull_simple("uk_inflation_YoY", uk_inflation["YoY"])
        if not df.empty: freq_hint["uk_inflation_YoY"] = "M" if _looks_monthly(df["Date"]) else "D"; dfs.append(df)

        # ---------- PLN inflation expectations (switch at each index 'start') ----------
        start_year_req = pd.to_datetime(start).year
        start_year_pln = max(2007, start_year_req)
        end_year_pln   = pd.to_datetime(end).year + 3  # small cushion to catch latest years

        series_by_year = {}
        first_date_by_year = {}

        for y in range(start_year_pln, end_year_pln + 1):
            tkr = f"ECPIPL {str(y)[-2:]} Index"
            raw = self.extraction_ticker(str(y), tkr, field, start, end, freq=freq)
            df_y = _normalize(raw, str(y))
            if not df_y.empty:
                series_by_year[y] = df_y
                first_date_by_year[y] = df_y["Date"].min()
                if include_components_sheet:
                    components_blocks.append(df_y.rename(columns={str(y): f"PLN_forecast_{y}"}))

        if series_by_year:
            # Order by actual first publication date (authoritative switch order)
            starts = pd.Series(first_date_by_year).sort_values()   # index: year, values: first date
            ordered_years  = starts.index.to_list()
            ordered_starts = starts.values

            # Business-day grid for requested window
            grid_start = pd.to_datetime(start)
            grid_end   = pd.to_datetime(end)
            bdays = pd.date_range(grid_start, grid_end, freq="B")

            # As-of (ffill) per year on the grid
            asof_by_year = {}
            for y in ordered_years:
                s = series_by_year[y].set_index("Date")[str(y)]
                s = s.reindex(bdays).ffill()
                asof_by_year[y] = s

            # Assemble expectations switching exactly on each 'start'
            out_vals = pd.Series(index=bdays, dtype=float)

            # Pre-start: extend first available value back to grid_start
            first_year  = ordered_years[0]
            first_start = pd.Timestamp(ordered_starts[0])
            first_start_eff = asof_by_year[first_year].first_valid_index()
            if first_start_eff is None:
                first_start_eff = bdays[0]
            first_val = asof_by_year[first_year].loc[first_start_eff]
            pre_mask = (bdays < max(first_start, bdays[0]))
            out_vals.loc[pre_mask] = first_val

            # From start(Y) to day before start(Y+1), inclusive of start(Y)
            from pandas.tseries.offsets import BDay
            for i, y in enumerate(ordered_years):
                seg_start = pd.Timestamp(ordered_starts[i])
                if i + 1 < len(ordered_years):
                    next_start = pd.Timestamp(ordered_starts[i + 1])
                    seg_end = next_start - BDay(1)
                    if seg_end < seg_start:
                        continue
                else:
                    seg_end = bdays[-1]
                mask = (bdays >= seg_start) & (bdays <= seg_end)
                if mask.any():
                    out_vals.loc[mask] = asof_by_year[y].loc[mask]

            df_pln_expect = pd.DataFrame({
                "Date": bdays,
                "pln_inflation_expectations": out_vals.values
            })

            # Mark as daily (no EOM snapping)
            freq_hint["pln_inflation_expectations"] = "D"
            dfs.append(df_pln_expect)

            if include_components_sheet:
                starts_df = starts.reset_index()
                starts_df.columns = ["Year", "FirstDate"]
                components_blocks.append(starts_df.sort_values("FirstDate"))

        # FX spot
        for k, v in fx_spot.items():
            nm = f"fx_{k}"; df = _pull_simple(nm, v)
            if not df.empty: freq_hint[nm] = "D"; dfs.append(df)
            
        # EURPLN basis
        for k, v in eurpln_basis.items():
            nm = f"eurpln_basis_{k}"; df = _pull_simple(nm, v)
            if not df.empty: freq_hint[nm] = "D"; dfs.append(df)

        # EURUSD/GBPUSD basis merged (legacy vs current; current wins)
        merged_basis = []
        components_blocks = []  # optional diagnostics
        for tenor in eurusd_tenors:
            nm = f"eurusd_basis_{tenor}"
            leg = eurusd_legacy.get(tenor); cur = eurusd_current.get(tenor)
            df_leg = _pull_simple(nm + "_legacy", leg) if leg else pd.DataFrame(columns=["Date", nm + "_legacy"])
            df_cur = _pull_simple(nm + "_current", cur) if cur else pd.DataFrame(columns=["Date", nm + "_current"])
            if include_components_sheet:
                components_blocks.append(pd.merge(df_leg, df_cur, on="Date", how="outer").sort_values("Date"))
            df_clean = _merge_keep_current(nm, df_leg, df_cur)
            if not df_clean.empty: freq_hint[nm] = "D"; merged_basis.append(df_clean)

        for tenor in gbpusd_tenors:
            nm = f"gbpusd_basis_{tenor}"
            leg = gbpusd_legacy.get(tenor); cur = gbpusd_current.get(tenor)
            df_leg = _pull_simple(nm + "_legacy", leg) if leg else pd.DataFrame(columns=["Date", nm + "_legacy"])
            df_cur = _pull_simple(nm + "_current", cur) if cur else pd.DataFrame(columns=["Date", nm + "_current"])
            if include_components_sheet:
                components_blocks.append(pd.merge(df_leg, df_cur, on="Date", how="outer").sort_values("Date"))
            df_clean = _merge_keep_current(nm, df_leg, df_cur)
            if not df_clean.empty: freq_hint[nm] = "D"; merged_basis.append(df_clean)

        dfs.extend(merged_basis)

        # -------------- Wide merge --------------
        if not dfs:
            print("No data downloaded.")
            return pd.DataFrame()

        df_final = dfs[0]
        for df in dfs[1:]:
            df_final = pd.merge(df_final, df, on="Date", how="outer")

        df_final["Date"] = pd.to_datetime(df_final["Date"], errors="coerce")
        df_final = df_final.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)

        # -------------- Reindex & fill --------------
        first_day = df_final["Date"].min()
        last_day  = df_final["Date"].max()
        bdays = pd.date_range(first_day, last_day, freq="B")
        df_final = df_final.set_index("Date").sort_index()
        orig = df_final.copy()
        df_final = df_final.reindex(bdays)

        for col in df_final.columns:
            if freq_hint.get(col) == "M":
                m = orig[col].dropna()
                idx_eom = pd.to_datetime(m.index) + MonthEnd(0)
                m.index = idx_eom
                eom_for_day = pd.to_datetime(df_final.index) + MonthEnd(0)
                df_final[col] = m.reindex(eom_for_day).values
            else:
                df_final[col] = df_final[col].ffill()

        df_final.index.name = "Date"
        df_final = df_final.reset_index()

        # -------------- Excel export --------------
        if out_xlsx:
            try:
                with pd.ExcelWriter(out_xlsx, engine="xlsxwriter") as xw:
                    df_final.to_excel(xw, index=False, sheet_name="merged_clean")
                    if include_components_sheet and components_blocks:
                        comp = components_blocks[0]
                        for cdf in components_blocks[1:]:
                            comp = pd.merge(comp, cdf, on="Date", how="outer")
                        comp.sort_values("Date", inplace=True)
                        comp.to_excel(xw, index=False, sheet_name="components_raw")
                print(f"Finished: {len(df_final)} rows, {df_final.shape[1]-1} series. Saved to {out_xlsx}")
            except Exception as e:
                print(f"Excel export failed: {e}")

        return df_final