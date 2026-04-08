Manage a self-hosted InvoiceNinja v5 instance from the command line using invoiceninja-cli.

Run the following command with the provided arguments:

```
invoiceninja-cli $ARGUMENTS
```

## Prerequisites

Install the CLI:
```bash
pip install git+https://github.com/nfaction/invoiceninja-cli
```

Configure it (one-time):
```bash
invoiceninja-cli configure
# or set env vars:
# export INVOICENINJA_URL=https://your-invoiceninja-host
# export INVOICENINJA_TOKEN=your_api_token
```

## Common commands

```bash
# List all invoices
invoiceninja-cli invoices list --all

# Find an invoice by number and get its ID
invoiceninja-cli invoices list --number 0168

# View line items on an invoice
invoiceninja-cli invoices items <ID>

# Edit a line item interactively
invoiceninja-cli invoices edit-item <ID>

# Send an invoice
invoiceninja-cli invoices send <ID>

# Mark an invoice paid
invoiceninja-cli invoices mark-paid <ID>

# List clients
invoiceninja-cli clients list --all

# List unpaid invoices
invoiceninja-cli invoices list --all --status unpaid

# Get JSON output for scripting
invoiceninja-cli invoices list --all --json
```

## All entity groups

clients, invoices, quotes, payments, products, tasks, projects, vendors, expenses, credits, recurring-invoices, purchase-orders

Each supports: list [--all] [--filter TEXT] [--json], get ID, create, update ID, delete ID, archive ID, restore ID
