---
name: invoiceninja-cli
version: "0.1.0"
description: CLI harness for InvoiceNinja v5 REST API
install: pip install invoiceninja-cli
binary: invoiceninja-cli
requires_config: true
config_method: "invoiceninja-cli configure OR env vars INVOICENINJA_URL + INVOICENINJA_TOKEN"
entities:
  - clients
  - invoices
  - quotes
  - payments
  - products
  - tasks
  - projects
  - vendors
  - expenses
  - recurring_invoices
  - purchase_orders
output_formats: [table, json]
json_flag: --json
---

# invoiceninja-cli Skill

This skill provides a CLI harness for managing an InvoiceNinja v5 self-hosted instance
via its REST API.

## Setup

1. Install: `pip install invoiceninja-cli`
2. Configure: `invoiceninja-cli configure`
   - Prompts for base URL (e.g. `https://invoiceninja.example.com`) and API token
   - Or set env vars: `INVOICENINJA_URL` + `INVOICENINJA_TOKEN`
3. Verify: `invoiceninja-cli ping`

## Entities

| Entity | Commands |
|--------|----------|
| `clients` | list, get, create, update, delete, archive, restore |
| `invoices` | list, get, create, update, delete, send, mark-paid, archive, restore |
| `quotes` | list, get, create, update, delete, approve, send, archive, restore |
| `payments` | list, get, create, update, delete, archive, restore |
| `products` | list, get, create, update, delete, archive, restore |
| `tasks` | list, get, create, update, delete, start, stop, archive, restore |
| `projects` | list, get, create, update, delete, archive, restore |
| `vendors` | list, get, create, update, delete, archive, restore |
| `expenses` | list, get, create, update, delete, archive, restore |
| `credits` | list, get, create, archive, restore |
| `recurring-invoices` | list, get, start, stop, archive, restore |
| `purchase-orders` | list, get, send, archive, restore |

## Common Patterns

```bash
# List with JSON output for scripting
invoiceninja-cli <entity> list --json

# Paginate large result sets
invoiceninja-cli clients list --page 2 --per-page 50

# Filter by text
invoiceninja-cli clients list --filter "acme"

# Bulk archive
invoiceninja-cli clients archive ID1 ID2 ID3

# Interactive shell
invoiceninja-cli repl
```

## Key Workflow: Invoice Lifecycle

```bash
# 1. Create client
invoiceninja-cli clients create --name "Client Co" --email "a@b.com"

# 2. Create invoice for that client
invoiceninja-cli invoices create --client-id <CID> --amount 1000 --due-date 2024-12-31

# 3. Email the invoice
invoiceninja-cli invoices send <IID>

# 4. Record payment when received
invoiceninja-cli payments create --client-id <CID> --invoice-id <IID> --amount 1000
```

## Error Handling

- HTTP 401: Invalid token — re-run `configure`
- HTTP 404: Wrong ID or base URL
- HTTP 422: Validation error — check required fields
- Network error: Check Kubernetes service accessibility
