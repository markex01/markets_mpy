from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def obtener_trimestre(mes):
    """Returns the quarter number for a given month.

    Args:
        mes (int): Month number (1-12).

    Returns:
        int: Quarter number (1-4), or 0 if the month is invalid.
    """
    if 1 <= mes <= 3:
        return 1
    elif 4 <= mes <= 6:
        return 2
    elif 7 <= mes <= 9:
        return 3
    elif 10 <= mes <= 12:
        return 4
    else:
        return 0

def days_in_month(year, month):
    """Returns the number of days in a given month.

    Args:
        year (int): The year (e.g. 2024).
        month (int): The month number (1-12).

    Returns:
        int: Number of days in the specified month.
    """
    # Get the first day of the month
    first_day = datetime(year, month, 1)
    # Calculate the first day of the next month and subtract one day to get the last day of the current month
    last_day = first_day + relativedelta(months=1) - timedelta(days=1)
    return last_day.day

def days_in_year(year):
    """Returns the number of days in a given year, accounting for leap years.

    Args:
        year (int): The year (e.g. 2024).

    Returns:
        int: 366 for leap years, 365 otherwise.
    """
    from calendar import isleap

    if isleap(year):
        return 366
    else:
        return 365


def map_dates (es_date):
    """Parses a Spanish-language date string into a date object.

    Expects the format "D de <mes> de YYYY" (e.g. "15 de enero de 2024").

    Args:
        es_date (str): Date string in Spanish format.

    Returns:
        datetime.date: Parsed date object.
    """
    months_mapping = {
        'enero': '01',
        'febrero': '02',
        'marzo': '03',
        'abril': '04',
        'mayo': '05',
        'junio': '06',
        'julio': '07',
        'agosto': '08',
        'septiembre': '09',
        'octubre': '10',
        'noviembre': '11',
        'diciembre': '12'
    }


    date_parts = es_date.split()
    day = date_parts[0]
    month = months_mapping[date_parts[2]]
    year = date_parts[-1]

    formatted_date_str = f"{day}-{month}-{year}"
    date_obj = datetime.strptime(formatted_date_str, "%d-%m-%Y").date()

    return (date_obj)

def map_month_abbr (month: str):

    """Returns the month number for a given English month abbreviation.
    Args:
        month (str): English month abbreviation (e.g. "Jan", "Feb", etc.).
    Returns:
        int: Month number (1-12).

    """
    months_mapping = {
        'Jan': 1,
        'Feb': 2,
        'Mar': 3,
        'Apr': 4,
        'May': 5,
        'Jun': 6,
        'Jul': 7,
        'Aug': 8,
        'Sep': 9,
        'Oct': 10,
        'Nov': 11,
        'Dec': 12
    }
    return (months_mapping[month])

def map_month (num):
    """Returns the English month name for a given month number.

    Args:
        num (int): Month number (1-12).

    Returns:
        str: Full English month name (e.g. "January").
    """
    months_mapping = {
        1: 'January',
        2: 'February',
        3: 'March',
        4: 'April',
        5: 'May',
        6: 'June',
        7: 'July',
        8: 'August',
        9: 'September',
        10: 'October',
        11: 'November',
        12: 'December'
    }
    return (months_mapping[num])

def unmap_month (month):
    """Returns the month number for a given English month name.

    Args:
        month (str): Full English month name (e.g. "January").

    Returns:
        int: Month number (1-12).
    """
    months_mapping = {
        'January': 1,
        'February': 2,
        'March': 3,
        'April': 4,
        'May': 5,
        'June': 6,
        'July': 7,
        'August': 8,
        'September': 9,
        'October': 10,
        'November': 11,
        'December': 12
    }
    return (months_mapping[month])

def map_month_folder (num):
    """Returns the Spanish folder name for a given month number.

    Used to construct paths matching the project's folder naming convention
    (e.g. "01. Enero" for month 1).

    Args:
        num (int): Month number (1-12).

    Returns:
        str: Folder name in the format "MM. <SpanishMonthName>".
    """
    months_mapping = {
        1: '01. Enero',
        2: '02. Febrero',
        3: '03. Marzo',
        4: '04. Abril',
        5: '05. Mayo',
        6: '06. Junio',
        7: '07. Julio',
        8: '08. Agosto',
        9: '09. Septiembre',
        10: '10. Octubre',
        11: '11. Noviembre',
        12: '12. Diciembre'
    }
    return (months_mapping[num])

def month_date_range(year, month):
    """Returns a list of all dates in a given month.

    Args:
        year (int): The year (e.g. 2024).
        month (int): The month number (1-12).

    Returns:
        list[datetime]: List of datetime objects for every day in the month,
            from the first to the last day inclusive.
    """
    start_date = datetime(year, month, 1)

    if month == 12:
        end_date = start_date.replace(year=start_date.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end_date = start_date.replace(month=start_date.month + 1, day=1) - timedelta(days=1)

    date_range = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]

    return date_range

def format_date (date: datetime):
    """Formats a datetime object as a YYYYMMDD string.

    Args:
        date (datetime): The date to format.

    Returns:
        str: Date string in "YYYYMMDD" format (e.g. "20240115").
    """
    if date.month < 10:
        month_str = '0' + str(date.month)
    else:
        month_str = str(date.month)

    if date.day < 10:
        day_str = '0' + str(date.day)
    else:
        day_str = str(date.day)

    date_formatted = str(date.year) + month_str + day_str
    return date_formatted

def most_recent_friday(ref_date=None):
    """Returns the most recent Friday on or before the reference date.

    Args:
        ref_date (datetime, optional): Reference date. Defaults to today
            if not provided.

    Returns:
        datetime.date: The most recent Friday as a date object.
    """
    if ref_date is None:
        ref_date = datetime.today()
    weekday = ref_date.weekday()  # Monday=0, Sunday=6
    days_since_friday = (weekday - 4) % 7
    most_recent = ref_date - timedelta(days=days_since_friday)
    return most_recent.date()

def get_start_date_from_quarterly(quarterly: str) -> str:
    """
    Get the start date from the quarterly string.
    Args:
        quarterly (str): Quarterly string in the format "YYQX", where YY is the last two digits of the year and X is the quarter number (1-4).
    Returns:
        start_date (str): Start date in the format "YYYY-MM-DD".
        end_date (str): End date in the format "YYYY-MM-DD".
    Raises:
        ValueError: If the quarter number is not between 1 and 4.
    """
    year = int(quarterly[:2]) + 2000
    quarter = int(quarterly[3])
    if quarter not in [1, 2, 3, 4]:
        raise ValueError("Quarter must be between 1 and 4.")
    if quarter < 4:
        month = (quarter) * 3 + 1
    else:
        month = 1
        year += 1
    date = datetime(year, month, 1)
    end_date = date - timedelta(days=1)
    start_date = end_date.replace(year=end_date.year - 2) + timedelta(days=1)
    # change to string format to be able to include in BloombergExtractor
    start_date = start_date.strftime("%Y-%m-%d")
    end_date = end_date.strftime("%Y-%m-%d")
    return start_date, end_date

def assign_quarter_strings(quarterly: str) -> tuple[int, int]:
    """Returns the first month and year of the period following a quarterly string.

    For quarters Q1-Q3, returns the first month of the next quarter in the
    same year. For Q4, rolls over to January of the following year.

    Args:
        quarterly (str): Quarterly string in the format "YYQX"
            (e.g. "25Q4" = Q4 2025).

    Returns:
        tuple[int, int]: A (month, year) tuple representing the first month
            of the quarter following the input.

    Raises:
        ValueError: If the quarter number is not between 1 and 4.
    """
    year = int(quarterly[:2]) + 2000
    quarter = int(quarterly[3])
    if quarter not in [1, 2, 3, 4]:
        raise ValueError("Quarter must be between 1 and 4.")
    if quarter < 4:
        month = (quarter) * 3 + 1
    else:
        month = 1
        year += 1
    return month, year

def get_quarterly_strings(quarterly: str) -> tuple[dict, str, str]:
    """Builds string variations for a quarterly label, used for filename matching.

    Returns a dictionary of year and quarter string aliases, plus the 4-digit
    year and the abbreviated start month of the quarter.

    Args:
        quarterly (str): Quarterly string in the format "YYQX"
            (e.g. "25Q2" = Q2 2025).

    Returns:
        tuple[dict, str, str]: A 3-element tuple:
            - dict: Contains keys "year" (list of 2- and 4-digit year strings)
              and "quarter" (list of quarter aliases like ["Q2", "APR", "APRIL"]).
            - str: 4-digit year as a string (e.g. "2025").
            - str: Abbreviated start month of the quarter (e.g. "Apr").

    Raises:
        ValueError: If the quarter number is not between 1 and 4.
    """
    quarter = int(quarterly[3])
    year = int(quarterly[:2]) + 2000
    year_list = [str(year), str(year)[2:]]

    if quarter == 1:
        quarter_list = ['Q1', 'Jan'.upper(), 'January'.upper()]
        quarter_month = 'Jan'
    elif quarter == 2:
        quarter_list = ['Q2', 'Apr'.upper(), 'April'.upper()]
        quarter_month = 'Apr'
    elif quarter == 3:
        quarter_list = ['Q3', 'Jul'.upper(), 'July'.upper()]
        quarter_month = 'Jul'
    elif quarter == 4:
        quarter_list = ['Q4', 'Oct'.upper(), 'October'.upper()]
        quarter_month = 'Oct'
    else:
        raise ValueError("Quarter must be between 1 and 4.")

    quarterly_dict ={
        'year': year_list,
        'quarter': quarter_list
    }

    quarter_year = str(year)

    return quarterly_dict, quarter_year, quarter_month
