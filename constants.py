import logging
import os
from datetime import datetime

import pytz
import taxjar
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("logger")
logging.basicConfig(level=logging.INFO)

taxjar_client = taxjar.Client(api_key=os.getenv("TAXJAR_API_KEY"))


def convert_timestamp_to_datetime_utc(timestamp):
    dt_naive_utc = datetime.utcfromtimestamp(timestamp)
    return dt_naive_utc.replace(tzinfo=pytz.utc).strftime("%Y-%m-%dT%H:%M:%S")


def get_customer_address(invoice):
    if invoice["customer_shipping"]:
        return invoice["customer_shipping"]["address"]
    elif invoice["customer_address"]:
        return invoice["customer_address"]
    elif invoice["charge"]["billing_details"]:
        return invoice["charge"]["billing_details"]["address"]
    else:
        return {
            "to_country": None,
            "to_zip": None,
            "to_state": None,
            "to_city": None,
            "to_street": None
        }


def create_taxjar_transaction(transaction, transaction_type):
    try:
        if transaction_type == "order":
            return taxjar_client.create_order(transaction)
        elif transaction_type == "refund":
            return taxjar_client.create_refund(transaction)
    except taxjar.exceptions.TaxJarConnectionError as err:
        logger.warning(err)
    except taxjar.exceptions.TaxJarResponseError as err:
        logger.warning(err.full_response)
