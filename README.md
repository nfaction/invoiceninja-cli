# invoiceninja-cli

A production-ready CLI harness for [InvoiceNinja v5](https://invoiceninja.com) self-hosted instances.
Wraps the InvoiceNinja REST API so you can manage every entity from the terminal or from agent scripts — no browser required.

Targets **InvoiceNinja v5.12.27** (v5-stable branch). The v5 API is backward-compatible across minor versions.

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Quick Start](#quick-start)
- [Command Reference](#command-reference)
  - [Global Options](#global-options)
  - [configure](#configure)
  - [ping](#ping)
  - [clients](#clients)
  - [invoices](#invoices)
  - [quotes](#quotes)
  - [payments](#payments)
  - [products](#products)
  - [tasks](#tasks)
  - [projects](#projects)
  - [vendors](#vendors)
  - [expenses](#expenses)
  - [credits](#credits)
  - [recurring-invoices](#recurring-invoices)
  - [purchase-orders](#purchase-orders)
  - [repl](#repl)
- [Output Formats](#output-formats)
- [Workflows](#workflows)
- [Running E2E Tests](#running-e2e-tests)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)

---

## Requirements

- Python 3.8+
- Access to a running InvoiceNinja v5 instance (self-hosted, e.g. on Kubernetes)
- An InvoiceNinja API token (Settings → API Tokens)

Dependencies installed automatically:

| Package | Purpose |
|---------|---------|
| `click` | CLI framework |
| `requests` | HTTP client |
| `tabulate` | Table formatting |
| `prompt_toolkit` | REPL shell |

---

## Installation

**From GitHub (recommended):**
```bash
pip install git+https://github.com/nfaction/invoiceninja-cli.git
```

**From a local clone:**
```bash
cd ~/dev/invoiceninja-cli
pip install -e .
```

Verify the binary is available:

```bash
invoiceninja-cli --version
```

---

## Configuration

### Option 1 — Interactive setup (recommended)

```bash
invoiceninja-cli configure
```

Prompts for:
- **Base URL** — your InvoiceNinja host, e.g. `https://invoiceninja.internal`
- **API token** — from InvoiceNinja → Settings → API Tokens

Config is saved to `~/.config/invoiceninja-cli/config.json` with mode `600` (token is not world-readable).

### Option 2 — Environment variables

```bash
export INVOICENINJA_URL=https://invoiceninja.internal
export INVOICENINJA_TOKEN=your_api_token_here
```

Environment variables always override the config file — useful for CI or scripting.

### Verify connectivity

```bash
invoiceninja-cli ping
```

---

## Quick Start

```bash
# Configure once
invoiceninja-cli configure

# List clients
invoiceninja-cli clients list

# Create an invoice and email it
invoiceninja-cli invoices create --client-id abc123 --amount 1500 --due-date 2025-05-01
invoiceninja-cli invoices send <INVOICE_ID>

# Get JSON output for scripting
invoiceninja-cli invoices list --status unpaid --json | jq '.[].number'
```

---

## Command Reference

### Global Options

Available on every command:

| Flag | Description |
|------|-------------|
| `--json` | Output raw JSON instead of a table |
| `--version` | Show package version |
| `--help` | Show help for any command or subcommand |

List commands also accept:

| Flag | Default | Description |
|------|---------|-------------|
| `--page N` | 1 | Page number |
| `--per-page N` | 20 | Records per page |
| `--filter TEXT` | — | Full-text search |

---

### configure

```bash
invoiceninja-cli configure
```

Interactively set the base URL and API token. Saved to `~/.config/invoiceninja-cli/config.json`.

---

### ping

```bash
invoiceninja-cli ping
```

Tests connectivity to the API. Exits 0 on success, 1 on failure.

---

### clients

```
invoiceninja-cli clients COMMAND [OPTIONS]
```

| Command | Description |
|---------|-------------|
| `list` | List clients |
| `get ID` | Get a single client |
| `create` | Create a new client |
| `update ID` | Update a client |
| `delete ID` | Delete a client |
| `archive ID...` | Archive one or more clients |
| `restore ID...` | Restore archived clients |

**List options:**

```bash
invoiceninja-cli clients list [--filter TEXT] [--page N] [--per-page N] [--json]
```

**Create options:**

```bash
invoiceninja-cli clients create \
  --name "Acme Corp" \
  --email "billing@acme.com" \
  --phone "+1-555-1234" \
  --address1 "123 Main St" \
  --city "Portland" \
  --state "OR" \
  --postal-code "97201" \
  --country-id 840
```

**Update options:** same flags as create, applied as a partial update.

**Table columns:** name, email, balance, paid\_to\_date, phone

---

### invoices

```
invoiceninja-cli invoices COMMAND [OPTIONS]
```

| Command | Description |
|---------|-------------|
| `list` | List invoices |
| `get ID` | Get a single invoice |
| `create` | Create an invoice with line items |
| `update ID` | Update an invoice (header fields and/or line items) |
| `items ID` | Show line items with indices and line totals |
| `add-item ID` | Append a product/service line item to an existing invoice |
| `add-task ID` | Attach a task as a paid-time line item |
| `edit-item ID` | Edit a line item — interactive picker or `--index N` + field flags |
| `remove-item ID` | Remove a line item by index |
| `delete ID` | Delete an invoice |
| `send ID` | Email the invoice to the client |
| `mark-paid ID` | Mark an invoice as paid |
| `archive ID...` | Archive one or more invoices |
| `restore ID...` | Restore archived invoices |

**List options:**

```bash
invoiceninja-cli invoices list \
  [--status paid|unpaid|overdue|draft|sent] \
  [--client-id ID] \
  [--number INV-001] \
  [--filter TEXT] \
  [--page N] [--per-page N] [--json]
```

**Create — simple (single amount):**

```bash
invoiceninja-cli invoices create \
  --client-id <CLIENT_ID> \
  --amount 1500.00 \
  --due-date 2025-05-01
```

**Create — with detailed line items (repeatable `--item-*` flags, one set per line item):**

```bash
invoiceninja-cli invoices create \
  --client-id <CLIENT_ID> \
  --due-date 2025-05-01 \
  --item-key CONSULT --item-qty 10 --item-cost 150 --item-notes "Oct consulting" \
  --item-key EXPENSES --item-qty 1  --item-cost 200 --item-notes "Travel"
```

Each `--item-key/--item-qty/--item-cost/--item-notes/--item-type` set corresponds to one line item.
`--item-type` choices: `product` (default), `service`, `unpaid-time`, `paid-time`.

**Create — attach tasks as line items:**

```bash
invoiceninja-cli invoices create \
  --client-id <CLIENT_ID> \
  --task-id <TASK_ID_1> \
  --task-id <TASK_ID_2>
```

**Update — replace all line items:**

```bash
invoiceninja-cli invoices update <ID> \
  --item-key SUPPORT --item-qty 5 --item-cost 100 --item-notes "Support hours" \
  --item-key LICENSE --item-qty 1 --item-cost 500 --item-notes "Annual license"
```

**Inspect and modify line items on an existing invoice:**

```bash
# See current items — indices, quantities, unit costs, line totals, type
invoiceninja-cli invoices items <INVOICE_ID>
# #  Key       Notes                   Qty  Unit cost    Total  Type     Task ID
# 0  CONSULT   Oct consulting           10     150.00  1500.00  Product
# 1  EXPENSES  Travel                    1     200.00   200.00  Product

# Append a product item
invoiceninja-cli invoices add-item <INVOICE_ID> \
  --product-key SUPPORT --qty 3 --cost 120 --notes "Support calls" --type service

# Attach a task
invoiceninja-cli invoices add-task <INVOICE_ID> --task-id <TASK_ID>

# Edit a line item — interactive (recommended): lists items, prompts for index,
# then prompts for each field with the current value pre-filled
invoiceninja-cli invoices edit-item <INVOICE_ID>

# Edit non-interactively — supply --index and only the fields to change
invoiceninja-cli invoices edit-item <INVOICE_ID> --index 0 --qty 12 --cost 160
invoiceninja-cli invoices edit-item <INVOICE_ID> --index 1 --notes "Travel + hotel"

# Remove item at index 1
invoiceninja-cli invoices remove-item <INVOICE_ID> --index 1
```

**Interactive edit session example:**

```
$ invoiceninja-cli invoices edit-item INV-001-id

Line items on invoice INV-001-id:

#  Key       Notes             Qty  Unit cost    Total  Type
0  CONSULT   Oct consulting     10     150.00  1500.00  Product
1  EXPENSES  Travel              1     200.00   200.00  Product

Select item to edit [0-1]: 0

Editing item #0  (press Enter to keep current value)

  Product key [CONSULT]:
  Notes / description [Oct consulting]: Nov consulting
  Quantity [10.0]: 15
  Unit cost [150.0]: 155
  Type [product]:

Updated item:

#  Key     Notes            Qty  Unit cost    Total  Type
0  CONSULT  Nov consulting    15     155.00  2325.00  Product

Save changes? [Y/n]: Y
✓ Item 'CONSULT' updated.
```

**Table columns:** number, client\_name, date, due\_date, amount, balance, status

---

### quotes

```
invoiceninja-cli quotes COMMAND [OPTIONS]
```

| Command | Description |
|---------|-------------|
| `list` | List quotes |
| `get ID` | Get a single quote |
| `create` | Create a quote |
| `update ID` | Update a quote |
| `delete ID` | Delete a quote |
| `approve ID` | Approve a quote |
| `send ID` | Email the quote to the client |
| `archive ID...` | Archive quotes |
| `restore ID...` | Restore archived quotes |

**Create options:**

```bash
invoiceninja-cli quotes create \
  --client-id <CLIENT_ID> \
  --amount 5000.00 \
  --valid-until 2025-05-31
```

---

### payments

```
invoiceninja-cli payments COMMAND [OPTIONS]
```

| Command | Description |
|---------|-------------|
| `list` | List payments |
| `get ID` | Get a payment |
| `create` | Record a payment |
| `update ID` | Update a payment |
| `delete ID` | Delete a payment |
| `archive ID...` | Archive payments |
| `restore ID...` | Restore payments |

**List options:**

```bash
invoiceninja-cli payments list [--client-id ID] [--filter TEXT] [--json]
```

**Create options:**

```bash
invoiceninja-cli payments create \
  --client-id <CLIENT_ID> \
  --invoice-id <INVOICE_ID> \
  --amount 1500.00 \
  --date 2025-04-10 \
  --type-id 1          # 1=bank transfer, 2=cash, 3=credit card, etc.
```

**Table columns:** number, client\_name, date, amount, method

---

### products

```
invoiceninja-cli products COMMAND [OPTIONS]
```

| Command | Description |
|---------|-------------|
| `list` | List products |
| `get ID` | Get a product |
| `create` | Create a product |
| `update ID` | Update a product |
| `delete ID` | Delete a product |
| `archive ID...` | Archive products |
| `restore ID...` | Restore products |

**Create options:**

```bash
invoiceninja-cli products create \
  --key "CONSULT-HR" \
  --notes "Hourly consulting rate" \
  --price 150.00 \
  --quantity 1
```

**Table columns:** product\_key, description, price, quantity

---

### tasks

```
invoiceninja-cli tasks COMMAND [OPTIONS]
```

| Command | Description |
|---------|-------------|
| `list` | List tasks |
| `get ID` | Get a task |
| `create` | Create a task |
| `update ID` | Update a task |
| `delete ID` | Delete a task |
| `start ID` | Start a task timer |
| `stop ID` | Stop a task timer |
| `archive ID...` | Archive tasks |
| `restore ID...` | Restore tasks |

**List options:**

```bash
invoiceninja-cli tasks list [--client-id ID] [--project-id ID] [--json]
```

**Create options:**

```bash
invoiceninja-cli tasks create \
  --description "Homepage wireframes" \
  --client-id <CLIENT_ID> \
  --project-id <PROJECT_ID> \
  --rate 150.00
```

**Table columns:** number, description, client\_name, status, duration

---

### projects

```
invoiceninja-cli projects COMMAND [OPTIONS]
```

| Command | Description |
|---------|-------------|
| `list` | List projects |
| `get ID` | Get a project |
| `create` | Create a project |
| `update ID` | Update a project |
| `delete ID` | Delete a project |
| `archive ID...` | Archive projects |
| `restore ID...` | Restore projects |

**Create options:**

```bash
invoiceninja-cli projects create \
  --name "Website Redesign" \
  --client-id <CLIENT_ID> \
  --budgeted-hours 40 \
  --task-rate 150.00
```

---

### vendors

```
invoiceninja-cli vendors COMMAND [OPTIONS]
```

| Command | Description |
|---------|-------------|
| `list` | List vendors |
| `get ID` | Get a vendor |
| `create` | Create a vendor |
| `update ID` | Update a vendor |
| `delete ID` | Delete a vendor |
| `archive ID...` | Archive vendors |
| `restore ID...` | Restore vendors |

---

### expenses

```
invoiceninja-cli expenses COMMAND [OPTIONS]
```

| Command | Description |
|---------|-------------|
| `list` | List expenses |
| `get ID` | Get an expense |
| `create` | Create an expense |
| `update ID` | Update an expense |
| `delete ID` | Delete an expense |
| `archive ID...` | Archive expenses |
| `restore ID...` | Restore expenses |

**List options:**

```bash
invoiceninja-cli expenses list [--client-id ID] [--vendor-id ID] [--json]
```

**Create options:**

```bash
invoiceninja-cli expenses create \
  --amount 250.00 \
  --date 2025-04-05 \
  --vendor-id <VENDOR_ID> \
  --client-id <CLIENT_ID> \
  --notes "SaaS subscription"
```

---

### credits

```
invoiceninja-cli credits COMMAND [OPTIONS]
```

| Command | Description |
|---------|-------------|
| `list` | List credits |
| `get ID` | Get a credit |
| `create` | Create a credit |
| `archive ID...` | Archive credits |
| `restore ID...` | Restore credits |

---

### recurring-invoices

```
invoiceninja-cli recurring-invoices COMMAND [OPTIONS]
```

| Command | Description |
|---------|-------------|
| `list` | List recurring invoices |
| `get ID` | Get a recurring invoice |
| `start ID` | Start sending a recurring invoice |
| `stop ID` | Pause a recurring invoice |
| `archive ID...` | Archive |
| `restore ID...` | Restore |

---

### purchase-orders

```
invoiceninja-cli purchase-orders COMMAND [OPTIONS]
```

| Command | Description |
|---------|-------------|
| `list` | List purchase orders |
| `get ID` | Get a purchase order |
| `send ID` | Email a purchase order |
| `archive ID...` | Archive |
| `restore ID...` | Restore |

---

### repl

```bash
invoiceninja-cli repl
```

Launches an interactive shell. Type any `invoiceninja-cli` subcommand without the prefix. Type `exit` or `quit` to leave.

```
invoiceninja> clients list --filter acme
invoiceninja> invoices list --status unpaid --json
invoiceninja> ping
```

---

## Output Formats

All commands default to human-readable table output.

```bash
# Table (default)
invoiceninja-cli clients list

# JSON — full API response, unwrapped from envelope
invoiceninja-cli clients list --json

# Pipe to jq
invoiceninja-cli invoices list --status unpaid --json | jq '.[].number'

# Paginate
invoiceninja-cli clients list --page 2 --per-page 50
```

---

## Workflows

### Invoice lifecycle

```bash
# 1. Create a client
invoiceninja-cli clients create \
  --name "Acme Corp" --email "billing@acme.com"
# note the returned ID

# 2. Create an invoice
invoiceninja-cli invoices create \
  --client-id <CLIENT_ID> --amount 1500 --due-date 2025-05-01

# 3. Send the invoice by email
invoiceninja-cli invoices send <INVOICE_ID>

# 4. Record payment when received
invoiceninja-cli payments create \
  --client-id <CLIENT_ID> --invoice-id <INVOICE_ID> --amount 1500

# or simply mark as paid
invoiceninja-cli invoices mark-paid <INVOICE_ID>
```

### Quote → Invoice

```bash
invoiceninja-cli quotes create \
  --client-id <CLIENT_ID> --amount 5000 --valid-until 2025-05-31

invoiceninja-cli quotes approve <QUOTE_ID>
# convert to invoice from the web UI or via API
```

### Project time tracking

```bash
invoiceninja-cli projects create \
  --name "Website Redesign" --client-id <CLIENT_ID> --budgeted-hours 40

invoiceninja-cli tasks create \
  --description "Homepage wireframes" \
  --client-id <CLIENT_ID> --project-id <PROJECT_ID>

invoiceninja-cli tasks start <TASK_ID>
# ... work ...
invoiceninja-cli tasks stop <TASK_ID>
```

### Bulk operations

```bash
# Archive multiple clients
invoiceninja-cli clients archive ID1 ID2 ID3

# Restore archived invoices
invoiceninja-cli invoices restore ID1 ID2

# Scripted bulk archive of all draft invoices older than 90 days
invoiceninja-cli invoices list --status draft --json \
  | jq -r '.[].id' \
  | xargs invoiceninja-cli invoices archive
```

---

## Running E2E Tests

Unit tests run without any network access (all HTTP calls are mocked):

```bash
cd ~/dev/invoiceninja-cli
pytest invoiceninja_cli/tests/test_core.py -v
# 130 passed
```

E2E tests require a live InvoiceNinja instance:

```bash
export INVOICENINJA_URL=https://invoiceninja.internal
export INVOICENINJA_TOKEN=your_token_here

pytest invoiceninja_cli/tests/test_full_e2e.py -v
```

To test the installed CLI binary via subprocess:

```bash
CLI_ANYTHING_FORCE_INSTALLED=1 pytest invoiceninja_cli/tests/test_full_e2e.py -v -k TestCLISubprocess
```

---

## Project Structure

```
~/dev/invoiceninja-cli/
├── README.md                          # This file
├── INVOICENINJA.md                    # SOP: API auth, workflows, rate limits
├── setup.py                           # Package config (invoiceninja-cli)
└── invoiceninja_cli/
    ├── __init__.py
    ├── invoiceninja_cli.py            # CLI entry point (Click)
    ├── core/
    │   ├── session.py                 # InvoiceNinjaSession + InvoiceNinjaAPIError
    │   ├── clients.py
    │   ├── invoices.py
    │   ├── quotes.py
    │   ├── payments.py
    │   ├── products.py
    │   ├── projects.py
    │   ├── tasks.py
    │   ├── vendors.py
    │   ├── expenses.py
    │   ├── credits.py
    │   ├── recurring_invoices.py
    │   └── purchase_orders.py
    ├── utils/
    │   ├── config.py                  # Config file + env var management
    │   └── output.py                  # Table / JSON formatting
    ├── skills/
    │   └── SKILL.md                   # AI-agent skill definition
    └── tests/
        ├── TEST.md                    # Test plan + results
        ├── test_core.py               # Unit tests (130 passing, no network)
        └── test_full_e2e.py           # E2E tests (require live API)
```

**Config file:** `~/.config/invoiceninja-cli/config.json` (mode 600)

**Env vars:** `INVOICENINJA_URL`, `INVOICENINJA_TOKEN`

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `HTTP 401 Unauthorized` | Bad or missing API token | Re-run `configure` or check `INVOICENINJA_TOKEN` |
| `HTTP 403 Forbidden` | Token lacks permissions | Generate a token with full access in InvoiceNinja settings |
| `HTTP 404 Not Found` | Wrong entity ID or base URL | Verify the ID exists; check `INVOICENINJA_URL` has no trailing slash issues |
| `HTTP 422 Unprocessable` | Missing required field | Check the error detail in the response; required fields vary by entity |
| `HTTP 429 Too Many Requests` | Rate limited | Reduce request frequency; use `--per-page` to batch |
| Connection refused / timeout | Service not reachable | Check your Kubernetes service is up and the URL is correct |
| `Missing required configuration` | Config not set | Run `invoiceninja-cli configure` or export env vars |
| `invoiceninja-cli: command not found` | Not installed | Run `pip install -e ~/dev/invoiceninja-cli` |
