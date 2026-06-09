"""
In this script, we define dictionaries that map security identifiers to their respective Bloomberg tickers.
These mappings facilitate easy retrieval of financial data for various securities.
"""

fx_rate_securities = {
    'EURUSD':'EURUSD BGN Curncy',
    'EURPLN':'EURPLN BGN Curncy',
    'EURGBP':'EURGBP BGN Curncy',
    'GBPUSD':'GBPUSD BGN Curncy',
    'USDJPY':'USDJPY BGN Curncy',
}

europe_daily_pool_securities = {
    'ES':'OMLPDAHD Index',
    'DE':'LPXBHRBS Index',
    'PT':'OMPTDAHD Index',
    'IT':'GMELITBS Index',
    'PL':'PXPEIDTB Index',
    'IR':'SEMODEAV Index',
    'UK':'PXPXBASE Index',
    'FR':'PWNXFRAV Index'
}

europe_hourly_pool_security_roots = {
    'UK':'N2EXH',
    'ES':'OMLPHR',
    'IT':'GMEPIT',
    'PL':'PXPEDA',
    'IR':'SEMODE',
    'DE':'LPXBHR',
    'FR':'PWNXFR'
}

# Inflation (YoY CPI) tickers
europe_inflation_securities = {
    "UK": "UKRPCJYR Index",
    "IR": "IECPIYOY Index",
    "PT": "PLCPYOY Index",
    "DE": "GRCP20YY Index",
    "ES": "SPIPCYOY Index",
    "PL": "POCPIYOY Index",
    "IT": "ITCPNICY Index",
    # "FR": None,
}

# Swap rate tickers (only those provided)
europe_swap_rate_securities = {
    "UK": "BPSWS10 BGN Curncy",
    "PL": "PZSW10 BGN Curncy",
    "EU": "EUSA10 BGN Curncy"
    # "ES": None,
    # "DE": None,
    # "PT": None,
    # "IT": None,
    # "IR": None,
    # "FR": None,
}

# Government 10Y tickers
europe_gov_10y_yield_securities = {
    "UK": "GUKG10 Index",
    "IR": "GIGB10YR Index",
    "PT": "GSPT10YR Index",
    "DE": "GDBR10 Index",
    "ES": "GTESP10YR Corp",
    "PL": "GTPLN10YR Corp",
    "IT": "GBTPGR10 Index",
    # "FR": None,  # not provided in your table
}

# Stock market index tickers
europe_stock_market_securities = {
    "UK": "UKX Index",
    "IR": "ISEQ Index",
    "PT": "PSI20 Index",
    "DE": "DAX Index",
    "ES": "IBEX Index",
    "PL": "WIG Index",
    "IT": "FTSEMIB Index",
    # "FR": None,  # not provided in your table
}

fx_forecast_securities = {
    "EURUSD": [
        "FCUSEU Q426 Index",
        "FCUSEU Q427 Index",
        "FCUSEU Q428 Index",
        "FCUSEU Q429 Index",
    ],
    "EURGBP": [
        "FCEUGB Q426 Index",
        "FCEUGB Q427 Index",
        "FCEUGB Q428 Index",
        "FCEUGB Q429 Index",
    ],
    "EURPLN": [
        "FCEUPL Q426 Index",
        "FCEUPL Q427 Index",
        "FCEUPL Q428 Index",
        "FCEUPL Q429 Index",
    ],
}

gas_securities = {
    "TTF Spot" : "TTFG1MON BCFV Index",
    "CO2 Spot" : "EECXM1 SONA Index",
    "API2 Spot" : "XA1 Comdty",
}

wtg_securities = {
    "Hot-Rolled Coil Spot" : "HER1 Comdty",
    # "Plate Steel" : "NE	STNWPLXW KLSH Index",
    "Plate Steel" : "STNWPLXW KLSH Index",
    "Rebar Spot" : "RBT1 COMB Comdty",
}

solar_n_bess_securities = {
    "Polysilicon" : "PVSIPR00 Index",
    "Lithium carbonate" : "LJC1 Comdty",
}

bop_bos_securities = {
    "Copper" : "LMCADS03 LME Comdty",
    "Aluminum" : "LMAHDS03 LME Comdty",
}