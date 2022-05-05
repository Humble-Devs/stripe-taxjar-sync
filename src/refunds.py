import logging
import os

import stripe
from dotenv import load_dotenv

from .constants import convert_timestamp_to_datetime_utc, create_taxjar_transaction, get_customer_address

load_dotenv()

logger = logging.getLogger("logger")
logging.basicConfig(level=logging.INFO)

stripe.api_key = os.getenv("STRIPE_API_KEY")
REQUEST_LIMIT = 100  # Should be 100


def get_refund_object(data):
    """
    Converts Stripe charge data into a TaxJar Order Transaction object
    :param data: Charge data returned from Stripe API
    :return: Dictionary representing a TaxJar Transaction object
    """

    # Retrieve customer's shipping address (Fallback on customer's address or billing details)
    customer_shipping = get_customer_address(data["charge"]["invoice"])

    return {
        "transaction_id": data["id"],
        "transaction_reference_id": data["charge"]["id"],
        "transaction_date": convert_timestamp_to_datetime_utc(data["created"]),
        "to_country": customer_shipping["country"],
        "to_zip": customer_shipping["postal_code"],
        "to_state": customer_shipping["state"],
        "to_city": customer_shipping["city"],
        "to_street": customer_shipping["line1"],
        "amount": data["charge"]["invoice"]["subtotal"] / 100,  # Amounts are represented in the smallest currency unit, i.e. cents
        "shipping": 0,  # Digital Products don't incur shipping costs
        "sales_tax": data["charge"]["invoice"]["tax"] / 100,  # Total Sales Tax is represented in smallest currency unit, i.e. cents
    }


def retrieve_refunds():
    logger.info(f" Retrieving all Refunds ...\n")

    # Retrieve All Refunds from Stripe API
    all_refunds = []
    has_more_refunds = True
    refunds_starting_after = None

    while has_more_refunds:
        # Retrieve Refunds from Stripe API
        refunds = stripe.Refund.list(
            limit=REQUEST_LIMIT,
            starting_after=refunds_starting_after,
            expand=["data.charge.invoice.charge"]
        )

        # Append refunds to the list of all Refunds
        all_refunds += refunds["data"]

        # Retrieve the last retrieved Refund
        refunds_starting_after = all_refunds[-1]["id"]

        # Check if there's more refunds to retrieve
        has_more_refunds = refunds["has_more"]

    return all_refunds


def create_refund_transactions(all_refunds):
    logger.info(f" Creating TaxJar Refunds ...\n")

    for idx, refund in enumerate(all_refunds):

        # Create a TaxJar Transaction if Charge was successfully paid
        if refund["status"] == "succeeded" and refund["charge"]["invoice"]:
            refund_object = get_refund_object(refund)

            # Create Transaction using TaxJar API
            refund_transaction = create_taxjar_transaction(refund_object, "refund")

            if refund_transaction:
                logger.info(
                    f" Total Amount Refunded: {refund_transaction.amount}\tSales Tax Collected: {refund_transaction.sales_tax}\n"
                )
        else:
            logger.info(f" [!] Skipping [{idx + 1}/{len(all_refunds)}] Refund")


def sync_refunds():
    # Retrieve a list of all refunds
    all_refunds = retrieve_refunds()

    logger.info(f" Retrieved the total number of {len(all_refunds)} refunds\n")

    # For every refund check if its status is set to "succeeded"
    # Compose a TaxJar Refund object.
    # Create TaxJar Refund Transaction.
    create_refund_transactions(all_refunds)
