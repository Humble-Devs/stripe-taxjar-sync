import logging
import os
import pytz
import stripe
import taxjar
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("logger")
logging.basicConfig(level=logging.INFO)

stripe.api_key = os.getenv("STRIPE_API_KEY")
taxjar_client = taxjar.Client(api_key=os.getenv("TAXJAR_API_KEY"))
REQUEST_LIMIT = 100
FROM_ADDRESS = {
    "ZIP": os.getenv("FROM_ZIP"),
    "COUNTRY": os.getenv("FROM_COUNTRY"),
    "STATE": os.getenv("FROM_STATE"),
    "CITY": os.getenv("FROM_CITY"),
    "STREET": os.getenv("FROM_STREET")
}


def convert_timestamp_to_datetime_utc(timestamp):
    dt_naive_utc = datetime.utcfromtimestamp(timestamp)
    return dt_naive_utc.replace(tzinfo=pytz.utc).strftime("%Y-%m-%dT%H:%M:%S")


def get_order_obj(data):
    """
    Converts Stripe charge data into a TaxJar Order Transaction object
    :param data: Charge data returned from Stripe API
    :return: Dictionary representing a TaxJar Transaction object
    """
    return {
        "transaction_id": data["id"],
        "transaction_date": convert_timestamp_to_datetime_utc(data["created"]),
        "from_country": FROM_ADDRESS["COUNTRY"],
        "from_zip": FROM_ADDRESS["ZIP"],
        "from_state": FROM_ADDRESS["STATE"],
        "from_city": FROM_ADDRESS["CITY"],
        "from_street": FROM_ADDRESS["STREET"],
        "to_country": data["billing_details"]["address"]["country"],
        "to_zip": data["billing_details"]["address"]["postal_code"],
        "to_state": data["billing_details"]["address"]["state"],
        "to_city": data["billing_details"]["address"]["city"],
        "to_street": data["billing_details"]["address"]["line1"],
        "amount": data["amount"] / 100,  # Amounts are represented in smallest currency unit, i.e. cents
        "shipping": 0  # Digital Products don't have shipping costs
    }


def get_refund_obj(data):
    """
    Converts Stripe charge data into a TaxJar Order Transaction object
    :param data: Charge data returned from Stripe API
    :return: Dictionary representing a TaxJar Transaction object
    """

    # Retrieve Charge corresponding to the given Refund
    corresponding_charge = stripe.Charge.retrieve(data["charge"])

    return {
        "transaction_id": data["id"],
        "transaction_reference_id": corresponding_charge["id"],
        "transaction_date": convert_timestamp_to_datetime_utc(data["created"]),
        "from_country": FROM_ADDRESS["COUNTRY"],
        "from_zip": FROM_ADDRESS["ZIP"],
        "from_state": FROM_ADDRESS["STATE"],
        "from_city": FROM_ADDRESS["CITY"],
        "from_street": FROM_ADDRESS["STREET"],
        "to_country": corresponding_charge["billing_details"]["address"]["country"],
        "to_zip": corresponding_charge["billing_details"]["address"]["postal_code"],
        "to_state": corresponding_charge["billing_details"]["address"]["state"],
        "to_city": corresponding_charge["billing_details"]["address"]["city"],
        "to_street": corresponding_charge["billing_details"]["address"]["line1"],
        "amount": -(data["amount"] / 100),  # Amounts are represented in smallest currency unit, i.e. cents
        "shipping": 0  # Digital Products don't have shipping costs
    }


def calculate_sales_tax(transaction):
    """
    Calculates Sales Tax using TaxJar API and returns a float value
    :param transaction: Dictionary representing TaxJar Transaction object
    :return: Float value representing Sales Tax to be collected
    """
    try:
        return taxjar_client.tax_for_order(transaction).amount_to_collect
    except taxjar.exceptions.TaxJarConnectionError as err:
        logger.warning(err)
    except taxjar.exceptions.TaxJarResponseError as err:
        logger.warning(err.full_response)


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


def main():
    logger.info(f" Retrieving all Charges ...\n")
    # Retrieve All Charges from Stripe API
    all_charges = []
    has_more_charges = True
    orders_starting_after = None
    refunds_starting_after = None

    while has_more_charges:
        # Retrieve Charges from Stripe API
        charges = stripe.Charge.list(limit=REQUEST_LIMIT, starting_after=orders_starting_after)

        # Append charges to the list of all Charges
        all_charges += charges["data"]

        # Retrieve the last retrieved Charge
        orders_starting_after = all_charges[-1]["id"]

        # Check if there's more charges to retrieve
        has_more_charges = charges["has_more"]

    logger.info(f" Retrieving all Refunds ...\n")
    # Retrieve All Refunds from Stripe API
    all_refunds = []
    has_more_refunds = True
    while has_more_refunds:
        # Retrieve Charges from Stripe API
        refunds = stripe.Refund.list(limit=REQUEST_LIMIT, starting_after=refunds_starting_after)

        # Append refunds to the list of all Refunds
        all_refunds += refunds["data"]

        # Retrieve the last retrieved Refund
        refunds_starting_after = all_refunds[-1]["id"]

        # Check if there's more charges to retrieve
        has_more_refunds = refunds["has_more"]

    logger.info(f"\n\nNumber of all Charges: {len(all_charges)}\nNumber of all Refunds: {len(all_refunds)}\n")

    # Turn Stripe Charges into TaxJar Order Transactions
    for idx, charge in enumerate(all_charges):
        logger.info(f" Processing [{idx + 1}/{len(all_charges)}] Order")
        # Create a TaxJar Transaction if Charge was successfully paid
        if charge["paid"]:
            order_obj = get_order_obj(charge)
            # Calculate Sales Tax using TaxJar API
            sales_tax = calculate_sales_tax(order_obj)

            # Create a Transaction in TaxJar if Sales Tax was successfully calculated
            if sales_tax:
                # Add missing necessary properties
                order_obj["sales_tax"] = sales_tax

                order_transaction = create_taxjar_transaction(order_obj, "order")

                if order_transaction:
                    logger.info(f" Order Amount: {order_transaction.amount}\nOrder Tax to Collect: {order_transaction.sales_tax}\n")

    # Turn Stripe Refunds into TaxJar Refund Transactions
    for idx, refund in enumerate(all_refunds):
        logger.info(f" Processing [{idx + 1}/{len(all_refunds)}] Refund")
        # Create a TaxJar Transaction if Refund was successful
        if refund["status"] == "succeeded":
            refund_obj = get_refund_obj(refund)
            # Calculate Sales Tax using TaxJar API
            sales_tax = calculate_sales_tax(refund_obj)

            # Create a Transaction in TaxJar if Sales Tax was successfully calculated
            if sales_tax:
                # Add missing necessary properties
                refund_obj["sales_tax"] = sales_tax

                refund_transaction = create_taxjar_transaction(refund_obj, "refund")

                if refund_transaction:
                    logger.info(f" Refund Amount: {refund_transaction.amount}\nRefund Tax to Collect: {refund_transaction.sales_tax}\n")


if __name__ == "__main__":
    main()
