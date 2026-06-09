from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def obtener_trimestre(mes):  
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
    # Get the first day of the month
    first_day = datetime(year, month, 1)
    # Calculate the first day of the next month and subtract one day to get the last day of the current month
    last_day = first_day + relativedelta(months=1) - timedelta(days=1)
    return last_day.day

def days_in_year(year):

    from calendar import isleap

    if isleap(year):
        return 366
    else:
        return 365


def map_dates (es_date):   
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

def map_month (num):

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

    start_date = datetime(year, month, 1)

    if month == 12:
        end_date = start_date.replace(year=start_date.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end_date = start_date.replace(month=start_date.month + 1, day=1) - timedelta(days=1)

    date_range = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]

    return date_range

def format_date (date: datetime):

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
    if ref_date is None:
        ref_date = datetime.today()
    weekday = ref_date.weekday()  # Monday=0, Sunday=6
    days_since_friday = (weekday - 4) % 7
    most_recent = ref_date - timedelta(days=days_since_friday)
    return most_recent.date()
