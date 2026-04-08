# Test Plan — invoiceninja-cli

## Test Strategy

Two test suites cover correctness and integration:

| Suite | File | Scope |
|-------|------|-------|
| Unit (mocked) | `test_core.py` | All core resource methods, session logic, config, output formatting |
| E2E (live API) | `test_full_e2e.py` | Real HTTP calls to a running InvoiceNinja instance |

---

## Unit Tests (`test_core.py`)

All HTTP calls are mocked with `unittest.mock.patch`. No network access required.

### Session Tests
- `TestInvoiceNinjaSession`
  - `test_get_calls_correct_url` — verifies URL construction
  - `test_post_sends_json_body` — verifies JSON serialization
  - `test_put_sends_json_body`
  - `test_delete_calls_delete`
  - `test_bulk_posts_correct_payload`
  - `test_api_error_raised_on_4xx`
  - `test_api_error_raised_on_5xx`
  - `test_204_returns_empty_dict`

### Config Tests
- `TestConfig`
  - `test_load_config_missing_file_returns_empty`
  - `test_save_and_load_roundtrip`
  - `test_get_config_env_vars_override`
  - `test_require_config_raises_when_missing_url`
  - `test_require_config_raises_when_missing_token`

### Core Resource Tests (per entity)
Each of `TestClientResource`, `TestInvoiceResource`, `TestQuoteResource`,
`TestPaymentResource`, `TestProductResource`, `TestProjectResource`,
`TestTaskResource`, `TestVendorResource`, `TestExpenseResource` covers:
  - `test_list_passes_params`
  - `test_get_calls_correct_path`
  - `test_create_posts_data`
  - `test_update_puts_data`
  - `test_delete_calls_delete`
  - `test_archive_bulk`
  - `test_restore_bulk`

InvoiceResource additionally:
  - `test_send_bulk_email`
  - `test_mark_paid_bulk`

QuoteResource additionally:
  - `test_approve_bulk`

### Output Tests
- `TestFormatOutput`
  - `test_json_mode_prints_json`
  - `test_table_mode_clients`
  - `test_table_mode_invoices`
  - `test_empty_records`
  - `test_single_record_unwrap`

---

## E2E Tests (`test_full_e2e.py`)

Skipped unless `INVOICENINJA_URL` and `INVOICENINJA_TOKEN` are set.

### TestLiveConnection
- `test_ping` — verifies the API is reachable

### TestLiveClients
- `test_create_list_get_delete_client` — full lifecycle

### TestLiveInvoices
- `test_create_and_list_invoice`

### TestLivePayments
- `test_create_payment`

### TestLiveProducts
- `test_create_and_delete_product`

### TestCLISubprocess
- `test_ping_command` — runs the CLI binary/module as a subprocess
- `test_clients_list_json` — verifies JSON output from `clients list --json`
- `test_invoices_list_table` — verifies table output

---

## Running Tests

```bash
# Unit tests only (no network required)
pytest tests/test_core.py -v

# E2E tests (requires live InvoiceNinja)
export INVOICENINJA_URL=https://invoiceninja.example.com
export INVOICENINJA_TOKEN=your_token
pytest tests/test_full_e2e.py -v

# All tests
pytest -v --tb=short tests/
```

---

## Test Results

### Run: 2026-04-07

**Environment:** Python 3.9.18, pytest 8.4.2, pyenv virtualenv `invoiceninja`

**Command:** `pytest -v --tb=short invoiceninja_cli/tests/`

**Result:** 130 passed, 15 skipped in 0.21s

```
platform darwin -- Python 3.9.18, pytest-8.4.2, pluggy-1.6.0
collected 145 items

test_core.py::TestInvoiceNinjaSession          12 passed
test_core.py::TestConfig                        7 passed
test_core.py::TestClientResource                9 passed
test_core.py::TestInvoiceResource              11 passed
test_core.py::TestQuoteResource                 9 passed
test_core.py::TestPaymentResource               8 passed
test_core.py::TestProductResource               7 passed
test_core.py::TestProjectResource               8 passed
test_core.py::TestTaskResource                 11 passed
test_core.py::TestVendorResource                7 passed
test_core.py::TestExpenseResource               8 passed
test_core.py::TestCreditResource                5 passed
test_core.py::TestRecurringInvoiceResource      5 passed
test_core.py::TestPurchaseOrderResource         4 passed
test_core.py::TestFormatOutput                 10 passed
test_core.py::TestCLISmoke                      9 passed

test_full_e2e.py::TestLiveConnection            1 skipped (no live API)
test_full_e2e.py::TestLiveClients               1 skipped
test_full_e2e.py::TestLiveInvoices              2 skipped
test_full_e2e.py::TestLiveProducts              1 skipped
test_full_e2e.py::TestLivePayments              1 skipped
test_full_e2e.py::TestCLISubprocess             9 skipped

======================== 130 passed, 15 skipped in 0.21s ========================
```

E2E tests skipped: `INVOICENINJA_URL` and `INVOICENINJA_TOKEN` not set.
To run E2E tests: `export INVOICENINJA_URL=... INVOICENINJA_TOKEN=... && pytest tests/test_full_e2e.py -v`
