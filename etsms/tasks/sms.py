import logging
import random
import string

from twilio.rest import Client

from etsms.app import app
import etsms.tasks.db as db
import config.settings as settings


LOG_FORMAT = '%(asctime)-15s %(clientip)s %(user)-8s %(levelname)s %(message)s'
logging.basicConfig(format=LOG_FORMAT)


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    soft_time_limit=30
)
def send_all_sms_for_today():
    logging.warning('Starting to send all SMS')
    row_ids = db.get_record_numbers(db.should_send_ethiopia_sms)
    # row_ids = db.get_record_numbers(db.should_send_usa_sms)
    logging.warning(f'All records found: {" ".join(str(x) for x in row_ids)}')
    for row_id in row_ids:
        send_one_sms_for_today.delay(row_id)


@app.task(
    rate_limit='10/m',
    autoretry_for=(Exception,),
    retry_backoff=True,
    soft_time_limit=30
)
def send_one_sms_for_today(row_id: int):
    logging.warning(f'Working on single SMS for row: {row_id}')
    google_sheet = db.get_google_sheet()
    worksheet = google_sheet.sheet1
    row = worksheet.row_values(row_id)
    if db.should_send_ethiopia_sms(row):
    # if db.should_send_usa_sms(row):
        to = db.extract_phone_number(row[db.COL_TO_NUMBER])
        body = row[db.COL_MESSAGE]
        result = send_ethiopia_sms(to, body)
        # result = send_usa_sms(to, body)
        logging.warning(f'Sent SMS for row {row_id} to "{to}" with body: "{body[:15]}..."')
        worksheet.update_cell(row_id, db.COL_TWILIO_SID + 1, str(result.sid))
        worksheet.update_cell(row_id, db.COL_TWILIO_TIMESTAMP + 1, str(result.date_created))
        if result.error_code:
            worksheet.update_cell(row_id, db.COL_TWILIO_ERROR_CODE + 1, str(result.error_code))
            worksheet.update_cell(row_id, db.COL_TWILIO_ERROR_MESSAGE + 1, str(result.error_message))
        logging.warning(f'Google sheet updated row: {row_id}')
    else:
        logging.warning(f'Never mind. Determined not to use row: {row_id}')


def send_usa_sms(to, body):
    from_ = get_twilio_number()
    return send_sms(to, from_, body)


def send_ethiopia_sms(to, body):
    from_ = settings.TWILIO_ETHIOPIA_FROM
    return send_sms(to, from_, body)


def get_twilio_number() -> str:
    return settings.TWILIO_NUMBER


def get_twilio_client() -> Client:
    account_sid = settings.TWILIO_ACCOUNT_SID
    auth_token = settings.TWILIO_AUTH_TOKEN
    client = Client(account_sid, auth_token)
    return client


def send_sms(to, from_, body):
    client = get_twilio_client()
    result = client.messages.create(
        to=to,
        from_=from_,
        body=body
    )
    return result