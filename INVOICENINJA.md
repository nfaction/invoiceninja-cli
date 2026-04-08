# InvoiceNinja SOP — invoiceninja-cli

## What is InvoiceNinja?

InvoiceNinja is an open-source invoicing, billing, and client-management platform designed
for freelancers and small businesses. It offers a full-featured REST API (v5) that this CLI
harness wraps. The user runs InvoiceNinja self-hosted on Kubernetes.

Key capabilities:
- Client management (contacts, addresses, custom fields)
- Invoice creation, sending via email, and payment recording
- Quote management and conversion to invoices
- Recurring invoices with configurable frequencies
- Expense tracking (billable and non-billable)
- Project and task time-tracking
- Product/service catalog
- Vendor and purchase order management
- Credits and refunds

---

## API Authentication

All API calls require two HTTP request headers:

| Header | Value |
|--------|-------|
| `X-API-TOKEN` | Your API token (generated in InvoiceNinja Settings > API Tokens) |
| `X-Requested-With` | `XMLHttpRequest` |

Additionally, `Accept: application/json` and `Content-Type: application/json` should be set
for all requests.

Base URL pattern: `https://<your-host>/api/v1/<entity>`

Example curl:
```bash
curl -s \
  -H "X-API-TOKEN: your_token_here" \
  -H "X-Requested-With: XMLHttpRequest" \
  -H "Accept: application/json" \
  https://invoiceninja.example.com/api/v1/clients
```

---

## CLI Configuration

### Option 1: Interactive setup
```bash
invoiceninja-cli configure
```
Saves config to `~/.config/invoiceninja-cli/config.json` (mode 600).

### Option 2: Environment variables
```bash
export INVOICENINJA_URL=https://invoiceninja.example.com
export INVOICENINJA_TOKEN=your_token_here
```
Environment variables always override the config file.

### Test connectivity
```bash
invoiceninja-cli ping
```

---

## Key Workflows

### 1. Create a client, then an invoice, send it, and record payment

```bash
# Step 1 — Create a client
invoiceninja-cli clients create \
  --name "Acme Corporation" \
  --email "billing@acme.com" \
  --phone "+1-555-1234"

# Step 2 — Note the client ID returned, then create an invoice
invoiceninja-cli invoices create \
  --client-id <CLIENT_ID> \
  --amount 1500.00 \
  --date 2024-01-15 \
  --due-date 2024-02-15 \
  --notes "Consulting services for January 2024"

# Step 3 — Email the invoice to the client
invoiceninja-cli invoices send <INVOICE_ID>

# Step 4 — Once paid, record the payment
invoiceninja-cli payments create \
  --client-id <CLIENT_ID> \
  --invoice-id <INVOICE_ID> \
  --amount 1500.00 \
  --date 2024-02-10

# Or simply mark it as paid
invoiceninja-cli invoices mark-paid <INVOICE_ID>
```

### 2. Create a quote and convert to invoice

```bash
# Create quote
invoiceninja-cli quotes create \
  --client-id <CLIENT_ID> \
  --amount 5000.00 \
  --valid-until 2024-02-28

# Approve the quote (marks as approved; convert to invoice from the web UI or API)
invoiceninja-cli quotes approve <QUOTE_ID>
```

### 3. Track project time

```bash
# Create a project
invoiceninja-cli projects create \
  --name "Website Redesign" \
  --client-id <CLIENT_ID> \
  --budgeted-hours 40 \
  --task-rate 150.00

# Log a task
invoiceninja-cli tasks create \
  --description "Homepage wireframes" \
  --client-id <CLIENT_ID> \
  --project-id <PROJECT_ID>
```

### 4. Set up a recurring invoice

```bash
# Create via API (use --json for full control)
invoiceninja-cli recurring-invoices list
invoiceninja-cli recurring-invoices start <ID>
invoiceninja-cli recurring-invoices stop <ID>
```

---

## Common Filters and Query Parameters

All list commands support:
- `--page N` — page number (default: 1)
- `--per-page N` — records per page (default: 20)
- `--filter TEXT` — full-text search across name/number/email fields

Entity-specific filters:
- `invoices list --status paid|unpaid|overdue|draft|sent`
- `invoices list --client-id <ID>`
- `invoices list --number INV-001`
- `payments list --client-id <ID>`
- `tasks list --client-id <ID>`
- `tasks list --project-id <ID>`
- `expenses list --vendor-id <ID>`
- `expenses list --client-id <ID>`

---

## Bulk Operations

Bulk actions operate on multiple records simultaneously via `POST /api/v1/<entity>/bulk`.

```bash
# Archive multiple clients
invoiceninja-cli clients archive ID1 ID2 ID3

# Restore archived invoices
invoiceninja-cli invoices restore ID1 ID2

# Delete multiple products
invoiceninja-cli products delete ID  # single record only; use archive for bulk soft-delete
```

Supported bulk actions per entity:
- All entities: `archive`, `restore`, `delete`
- Invoices: additionally `email` (send), `mark_paid`, `mark_sent`
- Quotes: additionally `approve`, `email`
- Recurring invoices: additionally `start`, `stop`
- Purchase orders: additionally `email`

---

## Output Formats

All commands default to human-readable table output. Pass `--json` for machine-readable JSON:

```bash
# Table output (default)
invoiceninja-cli clients list

# JSON output
invoiceninja-cli clients list --json

# Pipe to jq
invoiceninja-cli invoices list --status unpaid --json | jq '.[].number'
```

---

## Rate Limits

InvoiceNinja self-hosted does not impose hard API rate limits by default. However, best
practices recommend:
- Avoid more than 60 requests/minute in automated scripts
- Use pagination (`--per-page`) rather than fetching all records in one call
- For bulk operations, prefer the `/bulk` endpoint over looping individual deletes/archives

---

## InvoiceNinja API Response Envelope

Most list endpoints return:
```json
{
  "data": [...],
  "meta": {
    "pagination": {
      "total": 100,
      "count": 20,
      "per_page": 20,
      "current_page": 1,
      "total_pages": 5
    }
  }
}
```

Single-record endpoints return:
```json
{
  "data": { ... }
}
```

---

## Troubleshooting

| Error | Likely Cause |
|-------|-------------|
| `HTTP 401` | Invalid or missing API token |
| `HTTP 403` | Token lacks permissions for this action |
| `HTTP 404` | Entity ID not found or wrong base URL |
| `HTTP 422` | Validation error — check required fields |
| `HTTP 429` | Rate limited |
| Connection refused | Wrong base URL or Kubernetes service not reachable |

---

## Version Compatibility

This CLI targets InvoiceNinja **v5.12.27**. The v5 API is stable; minor version bumps are
generally backward-compatible. Major entity schema fields referenced here are stable since
v5.5.x.
