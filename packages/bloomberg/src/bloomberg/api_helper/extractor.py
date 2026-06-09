from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

import pandas as pd
import blpapi


# Type alias for flexible date input: accept strings, date objects, or datetime objects
DateLike = Union[str, date, datetime]


@dataclass(frozen=True)
class BloombergConfig:
    """
    Configuration settings for Bloomberg API connection.
    frozen=True means instances are immutable (cannot be modified after creation).
    
    Attributes:
        host: Server address where Bloomberg Terminal is running (default: localhost)
        port: Port number for Bloomberg connection (default: 8194)
        refdata_service: Bloomberg service for reference data queries (BDP/BDH/intraday)
        instruments_service: Bloomberg service for instrument/ticker lookups
    """
    host: str = "localhost"
    port: int = 8194
    refdata_service: str = "//blp/refdata"
    instruments_service: str = "//blp/instruments"


class BloombergExtractor:
    """
    Main class for extracting financial data from Bloomberg Terminal.
    
    Bloomberg API provides three main request types:
    1. BDP (Reference Data): Get static/point-in-time data (e.g., current price, company name)
    2. BDH (Historical Data): Get time series with different frequencies (Daily/Weekly/Monthly/etc)
    3. Intraday Bars: Get high-frequency data like hourly or minute-level bars
    
    Supported extraction types:
    - bdp: reference/point-in-time fields (e.g., PX_LAST, NAME)
    - bdh: historical time series with periodicity (D/W/M/Q/Y)
    - intraday_bars: intraday bars for resolutions like hourly/minute

    Notes:
    - Hourly resolution is intraday bars (interval in minutes, e.g. 60 for hourly).
    - Monthly/Quarterly/Yearly are handled via HistoricalDataRequest periodicitySelection.
    - Some tickers/fields require entitlements.
    """

    # Maps user-friendly periodicity codes to Bloomberg's periodicity names
    # Used when requesting historical data to specify time interval granularity
    _HIST_PERIODICITY = {
        "D": "DAILY",      # Daily data
        "W": "WEEKLY",     # Weekly data
        "M": "MONTHLY",    # Monthly data
        "Q": "QUARTERLY",  # Quarterly data
        "Y": "YEARLY",     # Yearly data
    }

    def __init__(self, config: BloombergConfig = BloombergConfig()) -> None:
        """
        Initialize the Bloomberg extractor.
        
        Args:
            config: BloombergConfig object with connection settings
        """
        self.config = config
        # Create and start a Bloomberg session (connection to Bloomberg Terminal)
        self.session: blpapi.Session = self._create_session()

    # -------------------------
    # Session lifecycle
    # -------------------------
    def _create_session(self) -> blpapi.Session:
        """
        Establish connection to Bloomberg Terminal and open required services.
        
        A "session" is a persistent connection to Bloomberg. Services must be
        explicitly opened to access specific data (refdata, instruments, etc).
        
        Returns:
            blpapi.Session: Active Bloomberg session
            
        Raises:
            ConnectionError: If session fails to start or services fail to open
        """
        # Create session options with host/port configuration
        options = blpapi.SessionOptions()
        options.setServerHost(self.config.host)
        options.setServerPort(self.config.port)

        # Create session object (not yet connected)
        session = blpapi.Session(options)
        
        # Attempt to connect to Bloomberg Terminal
        if not session.start():
            raise ConnectionError(
                f"Failed to start Bloomberg session (host={self.config.host}, port={self.config.port})."
            )
        print(f"Bloomberg session started (host={self.config.host}, port={self.config.port})")

        # Open the reference data service (needed for BDP, BDH, intraday requests)
        if not session.openService(self.config.refdata_service):
            raise ConnectionError(f"Failed to open service {self.config.refdata_service}")
        print(f"Bloomberg service opened: {self.config.refdata_service}")

        # Open the instruments service (optional, but useful for ticker search/lookup)
        if not session.openService(self.config.instruments_service):
            raise ConnectionError(f"Failed to open service {self.config.instruments_service}")
        print(f"Bloomberg service opened: {self.config.instruments_service}")

        return session

    def close(self) -> None:
        """Stop the Bloomberg session and release resources."""
        if self.session:
            self.session.stop()
            print("Bloomberg session stopped")

    def __enter__(self) -> "BloombergExtractor":
        """
        Context manager entry: allows using 'with BloombergExtractor() as extractor:'
        Returns self so the 'as' variable refers to this object.
        """
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        """
        Context manager exit: automatically closes Bloomberg session when exiting 'with' block.
        Parameters (exc_type, exc, tb) are provided by Python but not used here.
        """
        self.close()

    # -------------------------
    # Public API
    # -------------------------
    def bdp(
        self,
        securities: Sequence[str],
        fields: Sequence[str],
        overrides: Optional[Dict[str, Any]] = None,
    ) -> pd.DataFrame:
        """
        Reference data (point-in-time). Equivalent of Excel BDP function.
        
        Retrieves static/current data for one or more securities and fields.
        Examples: current price (PX_LAST), company name (NAME), market cap, etc.
        
        Args:
            securities: List of ticker symbols (e.g., ["IBM US Equity", "AAPL US Equity"])
            fields: List of Bloomberg fields to retrieve (e.g., ["PX_LAST", "NAME"])
            overrides: Optional dict of override parameters for complex requests
            
        Returns:
            DataFrame indexed by security, with fields as columns
            Example:
                              PX_LAST          NAME
                security
                IBM US Equity    123.45  International Business Machines
                AAPL US Equity   175.50  Apple Inc
        """
        svc = self.session.getService(self.config.refdata_service)
        req = svc.createRequest("ReferenceDataRequest")

        # Add each security to the request
        for s in securities:
            req.append("securities", s)
        # Add each field to the request
        for f in fields:
            req.append("fields", f)

        self._apply_overrides(req, overrides)

        # Send request to Bloomberg and wait for response
        self.session.sendRequest(req)
        # Parse the response into a dictionary
        data = self._collect_refdata_response(fields=fields)

        # Convert dictionary to DataFrame
        df = pd.DataFrame.from_dict(data, orient="index")
        df.index.name = "security"
        return df

    def bdh(
        self,
        security: str,
        fields: Sequence[str],
        start: DateLike,
        end: DateLike,
        periodicity: str = "D",
        overrides: Optional[Dict[str, Any]] = None,
        adjust: bool = True,
        fill: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Historical data. Equivalent of Excel BDH function.
        
        Retrieves time series data for a single security across a date range.
        Can request different frequencies: daily, weekly, monthly, etc.
        
        Args:
            security: Single ticker symbol (e.g., "IBM US Equity")
            fields: List of fields to retrieve (e.g., ["PX_OPEN", "PX_LAST", "VOLUME"])
            start: Start date as string, date, or datetime
            end: End date as string, date, or datetime
            periodicity: Data frequency - "D" (daily), "W" (weekly), "M" (monthly), etc.
            overrides: Optional dict of override parameters
            adjust: If True, apply split/dividend adjustments to prices
            fill: How to handle non-trading days ("PREVIOUS", "NIL", etc.)
            
        Returns:
            DataFrame with date as index and fields as columns
            Example:
                        PX_OPEN  PX_LAST    VOLUME
                date
                2024-01-01    120.0    121.5  1000000
                2024-01-02    121.5    123.0   950000
        """
        per = periodicity.upper().strip()
        if per not in self._HIST_PERIODICITY:
            raise ValueError(f"Invalid periodicity={periodicity}. Use one of {list(self._HIST_PERIODICITY.keys())}")

        svc = self.session.getService(self.config.refdata_service)
        req = svc.createRequest("HistoricalDataRequest")

        # Add security (note: "securities" is plural, even though we're adding one)
        req.append("securities", security)

        # Add each field we want historical data for
        for f in fields:
            req.append("fields", f)

        # Set date range (convert to YYYYMMDD format)
        req.set("startDate", self._to_yyyymmdd(start))
        req.set("endDate", self._to_yyyymmdd(end))
        # Set the time period for grouping data
        req.set("periodicitySelection", self._HIST_PERIODICITY[per])

        # Enable price adjustments if requested (split/dividend adjustments)
        if adjust:
            req.set("adjustmentSplit", True)
            req.set("adjustmentNormal", True)
            req.set("adjustmentAbnormal", True)

        # Handle non-trading days (weekends, holidays)
        if fill is not None:
            req.set("nonTradingDayFillOption", fill)

        self._apply_overrides(req, overrides)

        # Send request and parse response
        self.session.sendRequest(req)
        rows = self._collect_historical_response(fields=fields)

        df = pd.DataFrame(rows)
        if df.empty:
            return df

        return df

    def intraday_bars(
        self,
        security: str,
        event_type: str,
        start: DateLike,
        end: DateLike,
        interval_minutes: int = 60,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> pd.DataFrame:
        """
        Intraday bars (e.g. hourly data). Great for power/commodity intraday analysis.
        
        Retrieves high-frequency bar data within a single day or across days.
        
        Args:
            security: Ticker symbol
            event_type: Type of data - 'TRADE' (actual trades), 'BID', 'ASK' (quote levels)
            start: Start datetime
            end: End datetime
            interval_minutes: Bar size in minutes (60 = hourly, 15 = 15-minute bars)
            overrides: Optional override parameters
            
        Returns:
            DataFrame indexed by time with OHLV (open, high, low, close, volume) data
            Example:
                              open    high     low   close    volume
                time
                2024-01-01 09:30:00  120.0  120.5  119.8  120.2  500000
                2024-01-01 10:30:00  120.2  121.0  120.0  120.8  450000
        """
        svc = self.session.getService(self.config.refdata_service)
        req = svc.createRequest("IntradayBarRequest")

        # Set the security
        req.set("security", security)
        # Set the event type (TRADE, BID, ASK, etc.)
        req.set("eventType", event_type)
        # Set bar interval size
        req.set("interval", int(interval_minutes))
        # Set date/time range (inclusive)
        req.set("startDateTime", self._to_datetime(start))
        req.set("endDateTime", self._to_datetime(end))

        self._apply_overrides(req, overrides)

        # Send request and parse response
        self.session.sendRequest(req)
        rows = self._collect_intraday_bar_response()

        df = pd.DataFrame(rows)
        if df.empty:
            return df
        df = df.set_index("time").sort_index()
        return df

    def get_chain_tickers(
        self,
        root_security: str,
        chain_field: str = "FUT_CHAIN",
        ticker_column_candidates: tuple[str, ...] = (
            "Security Description",
            "Ticker",
            "ticker",
            "Security",
            "Member Ticker and Exchange Code",
        ),
        debug: bool = False,
    ) -> list[str]:
        """
        Extract list of futures contracts for a root security (e.g., all available expiries).
        
        Some Bloomberg fields return tables (bulk data) instead of scalar values.
        FUT_CHAIN is one such field that lists all contracts in a futures chain.
        This method extracts ticker symbols from that table.
        
        Args:
            root_security: Root ticker (e.g., "ES" for S&P 500 futures)
            chain_field: Bloomberg field containing the chain (default: "FUT_CHAIN")
            ticker_column_candidates: Possible column names in the returned table
            debug: If True, print column names found in the response for debugging
            
        Returns:
            List of ticker symbols for all contracts in the chain
            Example: ["ESZ3", "ESH4", "ESM4", ...]
        """
        svc = self.session.getService(self.config.refdata_service)
        req = svc.createRequest("ReferenceDataRequest")
        req.append("securities", root_security)
        req.append("fields", chain_field)

        # Send request
        self.session.sendRequest(req)

        tickers: list[str] = []
        printed_columns = False

        # Bloomberg returns responses as events; process them until RESPONSE event ends
        while True:
            ev = self.session.nextEvent()
            for msg in ev:
                if msg.messageType() != blpapi.Name("ReferenceDataResponse"):
                    continue

                # Get the security data element from response
                sec_data = msg.getElement("securityData").getValueAsElement(0)
                field_data = sec_data.getElement("fieldData")

                if not field_data.hasElement(chain_field):
                    raise ValueError(f"Field {chain_field} not found for {root_security}")

                # Get the bulk field (table) containing the chain data
                bulk = field_data.getElement(chain_field)

                # Iterate through each row in the table
                for i in range(bulk.numValues()):
                    row = bulk.getValueAsElement(i)

                    # Print column names once for debugging
                    if debug and not printed_columns:
                        cols = [row.getElement(j).name().string() for j in range(row.numElements())]
                        print(f"[DEBUG] Bulk field '{chain_field}' columns: {cols}")
                        printed_columns = True

                    # Try to find a ticker-like column using common names
                    val = None
                    for col in ticker_column_candidates:
                        if row.hasElement(col):
                            val = row.getElementAsString(col)
                            break

                    # Fallback: use first element if no known column matched
                    if val is None and row.numElements() > 0:
                        val = str(row.getElement(0).getValue())

                    if val:
                        tickers.append(val)

            # Stop when we receive the final RESPONSE event
            if ev.eventType() == blpapi.Event.RESPONSE:
                break

        if not tickers:
            raise ValueError(
                f"No tickers extracted from {root_security} using field {chain_field}. "
                f"Try debug=True to inspect bulk columns."
            )

        return tickers

    # -------------------------
    # Helpers: overrides + parsing
    # -------------------------
    def _apply_overrides(self, request: blpapi.Request, overrides: Optional[Dict[str, Any]]) -> None:
        """
        Apply Bloomberg overrides to a request.
        
        Overrides are special parameters that modify how Bloomberg calculates/returns data.
        Example: requesting prices in a different currency, or using a specific accounting period.
        
        Args:
            request: Bloomberg request object to modify
            overrides: Dict mapping field names to values
                       Example: {"EQY_FUND_CRNCY": "USD", "BEST_FPERIOD_OVERRIDE": "1FY"}
                       
        Raises:
            ValueError: If the request type doesn't support overrides
        """
        if not overrides:
            return

        if not request.hasElement("overrides"):
            # Some request types don't support overrides; fail fast to avoid silent issues
            raise ValueError("This request type does not support overrides.")

        # Get the overrides element and add each override as a sub-element
        ov = request.getElement("overrides")
        for field_id, value in overrides.items():
            item = ov.appendElement()
            item.setElement("fieldId", str(field_id))
            item.setElement("value", value)

    def _collect_refdata_response(self, fields: Sequence[str]) -> Dict[str, Dict[str, Any]]:
        """
        Parse a ReferenceDataResponse message from Bloomberg.
        
        Bloomberg sends responses as events containing messages. This method reads
        all events/messages until the RESPONSE event completes, and parses them
        into a dictionary structure.
        
        Returns:
            Dict mapping security names to dicts of {field: value}
            Example:
                {
                    "IBM US Equity": {"PX_LAST": 123.45, "NAME": "IBM"},
                    "AAPL US Equity": {"PX_LAST": 175.50, "NAME": "Apple"}
                }
        """
        results: Dict[str, Dict[str, Any]] = {}

        # Keep processing events until we get the final RESPONSE event
        while True:
            ev = self.session.nextEvent()
            for msg in ev:
                if msg.messageType() != blpapi.Name("ReferenceDataResponse"):
                    continue

                # Get the array of security data from response
                sec_data = msg.getElement("securityData")
                for i in range(sec_data.numValues()):
                    # Extract one security's data
                    sec = sec_data.getValueAsElement(i)
                    sec_name = sec.getElementAsString("security")

                    # Get the field data element
                    field_data = sec.getElement("fieldData")
                    row: Dict[str, Any] = {}

                    # Extract each requested field
                    for f in fields:
                        if field_data.hasElement(f):
                            el = field_data.getElement(f)
                            # Convert Bloomberg element to Python value
                            row[f] = self._element_to_python(el)
                        else:
                            row[f] = None

                    results[sec_name] = row

            if ev.eventType() == blpapi.Event.RESPONSE:
                break

        return results

    def _collect_historical_response(self, fields: Sequence[str]) -> List[Dict[str, Any]]:
        """
        Parse a HistoricalDataResponse message from Bloomberg.
        
        Similar to _collect_refdata_response, but returns a list of data points
        (one per date) instead of grouped by security.
        
        Returns:
            List of dicts, one per date point
            Example:
                [
                    {"date": date(2024,1,1), "PX_OPEN": 120.0, "PX_LAST": 121.5},
                    {"date": date(2024,1,2), "PX_OPEN": 121.5, "PX_LAST": 123.0}
                ]
        """
        rows: List[Dict[str, Any]] = []

        while True:
            ev = self.session.nextEvent()
            for msg in ev:
                if msg.messageType() != blpapi.Name("HistoricalDataResponse"):
                    continue

                sec_data = msg.getElement("securityData")
                fd = sec_data.getElement("fieldData")

                # Iterate through each date/time point in the time series
                for i in range(fd.numValues()):
                    point = fd.getValueAsElement(i)
                    # Extract the date from this point
                    d = point.getElementAsDatetime("date")
                    # Convert datetime to date if necessary
                    if isinstance(d, datetime):
                        d = d.date()

                    # Create a row with the date and all field values
                    row: Dict[str, Any] = {"date": d}
                    for f in fields:
                        row[f] = self._element_to_python(point.getElement(f)) if point.hasElement(f) else None
                    rows.append(row)

            if ev.eventType() == blpapi.Event.RESPONSE:
                break

        return rows

    # -------------------------
    # Utility conversions
    # -------------------------
    @staticmethod
    def _to_yyyymmdd(x: DateLike) -> str:
        """
        Convert a date-like object to Bloomberg's date string format (YYYYMMDD).
        
        Bloomberg expects dates in YYYYMMDD format for requests.
        
        Args:
            x: String, date, or datetime object
            
        Returns:
            String in format YYYYMMDD (e.g., "20240101")
        """
        if isinstance(x, str):
            # Accept "YYYYMMDD" or "YYYY-MM-DD" formats
            s = x.strip()
            if len(s) == 8 and s.isdigit():
                return s
            return s.replace("-", "")
        if isinstance(x, datetime):
            return x.strftime("%Y%m%d")
        if isinstance(x, date):
            return x.strftime("%Y%m%d")
        raise TypeError(f"Unsupported date type: {type(x)}")

    @staticmethod
    def _to_datetime(x: DateLike) -> datetime:
        """
        Convert a date-like object to a datetime object.
        
        Used for intraday requests which require full datetime (with time component).
        
        Args:
            x: String, date, or datetime object
            
        Returns:
            datetime object
        """
        if isinstance(x, datetime):
            return x
        if isinstance(x, date):
            # Convert date to datetime at midnight
            return datetime(x.year, x.month, x.day)
        if isinstance(x, str):
            s = x.strip()
            # Try ISO format first (YYYY-MM-DD HH:MM:SS)
            try:
                return datetime.fromisoformat(s)
            except ValueError:
                # Try compact format (YYYYMMDD)
                if len(s) == 8 and s.isdigit():
                    return datetime(int(s[0:4]), int(s[4:6]), int(s[6:8]))
        raise TypeError(f"Unsupported date type: {type(x)}")

    @staticmethod
    def _safe_get(el: blpapi.Element, name: str) -> Any:
        """
        Safely extract a sub-element's value, returning None if it doesn't exist.
        
        Prevents errors when accessing optional fields.
        
        Args:
            el: Bloomberg element to search
            name: Name of sub-element to extract
            
        Returns:
            The element's value, or None if not found
        """
        if el.hasElement(name):
            return BloombergExtractor._element_to_python(el.getElement(name))
        return None

    @staticmethod
    def _element_to_python(el: blpapi.Element) -> Any:
        """
        Convert a Bloomberg Element to a native Python value.
        
        Bloomberg's C++ API returns "Element" objects that need conversion to
        Python types (int, float, str, etc.). This method handles the conversion.
        
        Args:
            el: Bloomberg Element object
            
        Returns:
            Python value (int, float, str, etc.) or string representation for complex types
        """
        try:
            # Most scalar types (int, float, bool, str, date) can be extracted with getValue()
            return el.getValue()
        except Exception:
            # Fallback for complex types that can't be directly converted
            return str(el)
