# Stripe <> TaxJar Sync
This repository synchronizes historical Stripe Orders and Refunds with TaxJar by creating Transactions using TaxJar API.

## Getting Started

1. Configure environment settings in `.env` file. Use template below:
```
STRIPE_API_KEY=<Your Stripe API Key>
TAXJAR_API_KEY=<Your TaxJar API Key>

FROM_ZIP=<Shipped From Zip Code>
FROM_COUNTRY=<Shipped From Country>
FROM_STATE=<Shipped From State>
FROM_CITY=<Shipped From City>
FROM_STREET=<Shipped From Street>
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Execute the algorithm:
```
python main.py
```
