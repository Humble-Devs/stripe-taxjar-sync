# Stripe <> TaxJar Sync
This repository synchronizes historical Stripe Orders and Refunds with TaxJar by creating Transactions using TaxJar API.

## Getting Started

1. Configure environment settings in `.env` file. Use template below:
```
STRIPE_API_KEY=<Your Stripe API Key>
TAXJAR_API_KEY=<Your TaxJar API Key>
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Execute the algorithm:
```
python -m src.main
```
