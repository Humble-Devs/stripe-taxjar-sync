import logging
import os

import stripe
from dotenv import load_dotenv

from constants import create_taxjar_transaction, convert_timestamp_to_datetime_utc, get_customer_address

load_dotenv()

logger = logging.getLogger("logger")
logging.basicConfig(level=logging.INFO)

stripe.api_key = os.getenv("STRIPE_API_KEY")
REQUEST_LIMIT = 100  # Should be 100


def get_order_object(data):
    """
    Converts Stripe charge data into a TaxJar Order Transaction object
    :param data: Charge data returned from Stripe API
    :return: Dictionary representing a TaxJar Transaction object
    """

    # Retrieve customer's shipping address (Fallback on customer's address or billing details)
    customer_shipping = get_customer_address(data)

    return {
        "transaction_id": data["id"],
        "transaction_date": convert_timestamp_to_datetime_utc(data["created"]),
        "to_country": customer_shipping["country"],
        "to_zip": customer_shipping["postal_code"],
        "to_state": customer_shipping["state"],
        "to_city": customer_shipping["city"],
        "to_street": customer_shipping["line1"],
        "amount": data["subtotal"] / 100,  # Amounts are represented in the smallest currency unit, i.e. cents
        "shipping": 0,  # Digital Products don't incur shipping costs
        "sales_tax": data["tax"] / 100,  # Total Sales Tax is represented in smallest currency unit, i.e. cents
    }


def retrieve_invoices():
    logger.info(f" Retrieving all Invoices ...\n")

    all_invoices = []
    has_more_invoices = True
    invoices_starting_after = None

    while has_more_invoices:
        # Retrieve Invoices from Stripe API
        invoices = stripe.Invoice.list(
            limit=os.getenv("REQUEST_LIMIT"),
            starting_after=invoices_starting_after,
            expand=["data.charge"]
        )

        # Append charges to the list of all Charges
        all_invoices += invoices["data"]

        # Retrieve the last retrieved Charge
        invoices_starting_after = all_invoices[-1]["id"]

        # Check if there's more charges to retrieve
        has_more_invoices = invoices["has_more"]

    return all_invoices


def create_order_transactions(all_invoices):
    logger.info(f" Creating TaxJar Orders ...\n")

    for idx, invoice in enumerate(all_invoices):

        # Create a TaxJar Transaction if Charge was successfully paid
        if invoice["paid"] and invoice["tax"]:
            logger.info(f" Processing [{idx + 1}/{len(all_invoices)}] Order")

            order = get_order_object(invoice)

            # Create Transaction using TaxJar API
            order_transaction = create_taxjar_transaction(order, "order")

            if order_transaction:
                logger.info(
                    f" Order Amount: {order_transaction.amount}\tOrder Tax Collected: {order_transaction.sales_tax}\n"
                )
        else:
            logger.info(f" [!] Skipping [{idx + 1}/{len(all_invoices)}] Order")


def sync_orders():
    # Retrieve a list of all invoices.
    all_invoices = retrieve_invoices()

    logger.info(f" Retrieved the total number of {len(all_invoices)} invoices\n")

    # For every invoice check if invoice was paid, and includes “sales tax” and “customer shipping” properties.
    # Compose a TaxJar Order object.
    # Create TaxJar Order Transaction.
    create_order_transactions(all_invoices)
