from .orders import sync_orders
from .refunds import sync_refunds


def main():
    # Synchronize Stripe Orders with TaxJar
    sync_orders()

    # Synchronize Stripe Refunds with TaxJar
    sync_refunds()


if __name__ == "__main__":
    main()
