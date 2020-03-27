import os
from typing import List

import arrow
import gspread
from oauth2client.service_account import ServiceAccountCredentials

import config.settings as settings


COL_COUNTRY = 0
COL_DATE_SCHEDULED = 1
COL_TO_NUMBER = 2
COL_MESSAGE = 3
COL_TWILIO_SID = 4
COL_TWILIO_TIMESTAMP = 5
COL_TWILIO_RESULT = 6
COL_TWILIO_RESPONSE = 7
COL_TWILIO_ERROR_CODE = 8
COL_TWILIO_ERROR_MESSAGE = 9


def get_google_sheet() -> gspread.models.Spreadsheet:
    client_secret = 'config/google-client-secret.json'
    scope = ['https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(client_secret, scope)
    client = gspread.authorize(creds)
    sheet_title = settings.SHEET_TITLE
    google_sheet = client.open(sheet_title)
    return google_sheet


def get_google_data(sheet_id: int, row_id: int) -> list:
    google_sheet = get_google_sheet()
    worksheet = google_sheet.get_worksheet(sheet_id)
    data = worksheet.row_values(row_id)
    return data


def now_within_time_range(min_hour_minute, max_hour_minute):
    now = arrow.utcnow()
    now_minutes = now.hour * 60 + now.minute
    min_minutes = min_hour_minute[0]*60 + min_hour_minute[1]
    max_minutes = max_hour_minute[0]*60 + max_hour_minute[1]
    return min_minutes <= now_minutes <= max_minutes



def get_date_in_ethiopia(format='YYYY-MM-DD') -> str:
    ethiopia_timestamp = arrow.now('Africa/Addis_Ababa')
    date = ethiopia_timestamp.format(format)
    return date


def get_date_in_usa(format='YYYY-MM-DD') -> str:
    usa_timestamp = arrow.now('America/New_York')
    date = usa_timestamp.format(format)
    return date


def should_send_usa_sms(row: list) -> bool:
    should_send = True
    # Make the row as long as it should be
    len_delta = COL_TWILIO_ERROR_MESSAGE - len(row)
    new_row = row + [''] * len_delta if len_delta > 0 else row
    today_in_usa = get_date_in_usa()
    if new_row[COL_COUNTRY] != 'USA':
        should_send = False
    elif new_row[COL_DATE_SCHEDULED] != today_in_usa:
        should_send = False
    elif not is_usa_number(new_row[COL_TO_NUMBER]):
        should_send = False
    elif new_row[COL_TWILIO_SID]:
        should_send = False
    elif not new_row[COL_MESSAGE]:
        should_send = False
    return should_send


def should_send_ethiopia_sms(row: list) -> bool:
    should_send = True
    # Make the row as long as it should be
    len_delta = COL_TWILIO_ERROR_MESSAGE - len(row)
    new_row = row + [''] * len_delta if len_delta > 0 else row
    today_in_ethiopia = get_date_in_ethiopia()
    if new_row[COL_COUNTRY] != 'Ethiopia':
        should_send = False
    elif new_row[COL_DATE_SCHEDULED] != today_in_ethiopia:
        should_send = False
    elif not is_ethiopian_number(new_row[COL_TO_NUMBER]):
        should_send = False
    elif new_row[COL_TWILIO_SID]:
        should_send = False
    elif not new_row[COL_MESSAGE]:
        should_send = False
    elif not now_within_time_range((5,30), (8,30)):
        should_send = False
    return should_send


def get_matching_records(validator):
    google_sheet = get_google_sheet()
    worksheets = google_sheet.worksheets()
    matches = []
    for i, sheet in enumerate(worksheets):
        if sheet.title.startswith('scheduled_'):
            data = sheet.get_all_values()
            these_matches = [j for j, row in enumerate(data, start=1) if validator(row)]
            matches.extend((i, j) for j in these_matches)
    return matches


def extract_phone_number(value) -> str:
    digits = [d for d in str(value) if d.isdigit()]
    return f"+{''.join(digits)}"


def is_ethiopian_number(value) -> bool:
    phone_number = extract_phone_number(value)
    return phone_number.startswith('+251') and len(phone_number) == 13


def is_usa_number(value) -> bool:
    phone_number = extract_phone_number(value)
    return phone_number.startswith('+1') and len(phone_number) == 12
