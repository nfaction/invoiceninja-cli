# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A CLI tool for managing a self-hosted InvoiceNinja v5 instance via its REST API. Supports all major entities (clients, invoices, quotes, payments, products, tasks, projects, vendors, expenses, credits, recurring invoices, purchase orders) with full CRUD and bulk operations.

## Commands

### Install and Setup
```bash
pip install -e .           # Install in development mode
pip install -e ".[dev]"    # Install with dev dependencies (pytest, responses, etc.)
invoiceninja-cli configure # Interactive setup: prompts for URL, API token, company ID
invoiceninja-cli ping      # Verify connectivity
```

### Testing
```bash
# Unit tests (all mocked, no network required)
pytest invoiceninja_cli/tests/test_core.py -v

# Single test
pytest invoiceninja_cli/tests/test_core.py -v -k "test_name"

# E2E tests (requires live InvoiceNinja instance)
export INVOICENINJA_URL=https://invoiceninja.internal
export INVOICENINJA_TOKEN=your_token_here
pytest invoiceninja_cli/tests/test_full_e2e.py -v
```

## Architecture

**Entry point:** `invoiceninja_cli/invoiceninja_cli.py` (1,845 lines) — all Click commands live here, one command group per entity. Commands use a `_handle_api()` wrapper for centralized error handling and output formatting.

**Layers:**

1. **CLI** (`invoiceninja_cli.py`) → Click commands call resource methods, wrap results in `_handle_api()`
2. **Resources** (`core/*.py`) → One class per entity (e.g., `InvoiceResource`). Standard interface: `list()`, `get()`, `create()`, `update()`, `delete()`, `archive()`, `restore()` plus entity-specific actions (e.g., `InvoiceResource.send()`, `TaskResource.start()`)
3. **Session** (`core/session.py`) → `InvoiceNinjaSession` handles all HTTP: auth headers (`X-API-TOKEN`), error conversion to `InvoiceNinjaAPIError`, pagination via `get_all_pages()`
4. **Config** (`utils/config.py`) → Reads `~/.config/invoiceninja-cli/config.json` (mode 600); env vars `INVOICENINJA_URL` / `INVOICENINJA_TOKEN` override the file
5. **Output** (`utils/output.py`) → `format_output()` produces human-readable tables (tabulate) or JSON; handles response envelope unwrapping, status ID humanization, pagination footers

**Data flow:**
```
CLI args → Click → resource.method(data) → session.post/get/put("/endpoint") → requests → InvoiceNinja API
                                                                                        ↓
Click output ← format_output() ← _handle_api() ← InvoiceNinjaAPIError (on failure) ←─┘
```

## Key Files

| File | Purpose |
|------|---------|
| `invoiceninja_cli/invoiceninja_cli.py` | All CLI commands (single large file) |
| `invoiceninja_cli/core/session.py` | HTTP session, auth, pagination, error handling |
| `invoiceninja_cli/utils/output.py` | Table/JSON output, entity column definitions, status labels |
| `invoiceninja_cli/utils/config.py` | Config file and env var loading |
| `INVOICENINJA.md` | API reference: auth headers, response envelope, workflows, error codes |
| `invoiceninja_cli/tests/test_core.py` | 130 unit tests — covers session, config, output, all resources |

## Adding a New Entity

1. Create `invoiceninja_cli/core/<entity>.py` following the pattern in any existing resource file
2. Add entity-specific columns to `utils/output.py` `ENTITY_COLUMNS` dict
3. Add status mappings if needed to `utils/output.py`
4. Add command group + subcommands to `invoiceninja_cli.py` following existing patterns
5. Add unit tests to `test_core.py`

## Configuration

Config file at `~/.config/invoiceninja-cli/config.json`:
```json
{
  "url": "https://invoiceninja.internal",
  "token": "your_api_token",
  "company_id": "optional"
}
```
Environment variables `INVOICENINJA_URL` and `INVOICENINJA_TOKEN` take precedence over the config file.
