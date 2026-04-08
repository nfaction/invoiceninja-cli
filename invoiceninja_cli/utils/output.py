"""Output formatting utilities for invoiceninja-cli."""

from __future__ import annotations

import json
from typing import Any, List, Optional

try:
    from tabulate import tabulate

    _HAS_TABULATE = True
except ImportError:
    _HAS_TABULATE = False

# ---------------------------------------------------------------------------
# Field definitions per entity type
# ---------------------------------------------------------------------------

_ENTITY_FIELDS: dict[str, list[tuple[str, str]]] = {
    "clients": [
        ("name", "Name"),
        ("id", "ID"),
        ("email", "Email"),
        ("balance", "Balance"),
        ("paid_to_date", "Paid To Date"),
        ("phone", "Phone"),
    ],
    "invoices": [
        ("number", "Number"),
        ("id", "ID"),
        ("client_name", "Client"),
        ("date", "Date"),
        ("due_date", "Due Date"),
        ("amount", "Amount"),
        ("balance", "Balance"),
        ("status_id", "Status"),
    ],
    "quotes": [
        ("number", "Number"),
        ("id", "ID"),
        ("client_name", "Client"),
        ("date", "Date"),
        ("valid_until", "Valid Until"),
        ("amount", "Amount"),
        ("status_id", "Status"),
    ],
    "payments": [
        ("number", "Number"),
        ("id", "ID"),
        ("client_name", "Client"),
        ("date", "Date"),
        ("amount", "Amount"),
        ("type_id", "Method"),
    ],
    "products": [
        ("product_key", "Product Key"),
        ("id", "ID"),
        ("notes", "Description"),
        ("price", "Price"),
        ("quantity", "Quantity"),
    ],
    "tasks": [
        ("number", "Number"),
        ("id", "ID"),
        ("description", "Description"),
        ("client_name", "Client"),
        ("status_id", "Status"),
        ("duration", "Duration"),
    ],
    "projects": [
        ("name", "Name"),
        ("id", "ID"),
        ("client_name", "Client"),
        ("due_date", "Due Date"),
        ("budgeted_hours", "Budgeted Hours"),
        ("task_rate", "Task Rate"),
    ],
    "vendors": [
        ("name", "Name"),
        ("id", "ID"),
        ("number", "Number"),
        ("city", "City"),
        ("phone", "Phone"),
    ],
    "expenses": [
        ("number", "Number"),
        ("id", "ID"),
        ("vendor_name", "Vendor"),
        ("client_name", "Client"),
        ("date", "Date"),
        ("amount", "Amount"),
    ],
    "credits": [
        ("number", "Number"),
        ("id", "ID"),
        ("client_name", "Client"),
        ("date", "Date"),
        ("amount", "Amount"),
        ("balance", "Balance"),
    ],
    "recurring_invoices": [
        ("number", "Number"),
        ("id", "ID"),
        ("client_name", "Client"),
        ("frequency_id", "Frequency"),
        ("next_send_date", "Next Send"),
        ("amount", "Amount"),
    ],
    "purchase_orders": [
        ("number", "Number"),
        ("id", "ID"),
        ("vendor_name", "Vendor"),
        ("date", "Date"),
        ("due_date", "Due Date"),
        ("amount", "Amount"),
    ],
}

# Human-readable invoice status mapping
_INVOICE_STATUS: dict[str, str] = {
    "1": "Draft",
    "2": "Sent",
    "3": "Partial",
    "4": "Paid",
    "5": "Cancelled",
    "6": "Reversed",
}

_QUOTE_STATUS: dict[str, str] = {
    "1": "Draft",
    "2": "Sent",
    "3": "Approved",
    "4": "Converted",
    "5": "Expired",
}

_TASK_STATUS: dict[str, str] = {
    "1": "Logged",
    "2": "Running",
    "3": "Paused",
    "4": "Billed",
}


def _resolve_field(record: dict, field: str) -> Any:
    """Extract a field from a record, with fallback for nested structures."""
    value = record.get(field, "")
    if value == "" and field == "client_name":
        client = record.get("client", {})
        if isinstance(client, dict):
            value = client.get("name", "")
    if value == "" and field == "vendor_name":
        vendor = record.get("vendor", {})
        if isinstance(vendor, dict):
            value = vendor.get("name", "")
    return value if value is not None else ""


def _humanize_status(entity: str, value: Any) -> str:
    """Convert numeric status IDs to human-readable strings."""
    s = str(value)
    if entity in ("invoices", "recurring_invoices"):
        return _INVOICE_STATUS.get(s, s)
    if entity == "quotes":
        return _QUOTE_STATUS.get(s, s)
    if entity == "tasks":
        return _TASK_STATUS.get(s, s)
    return s


def _extract_row(record: dict, fields: list[tuple[str, str]], entity: str) -> list:
    """Extract ordered values from a record for tabular display."""
    row = []
    for field, _ in fields:
        val = _resolve_field(record, field)
        if field == "status_id":
            val = _humanize_status(entity, val)
        row.append(val)
    return row


def _detect_entity(data: Any) -> str:
    """Attempt to infer entity type from response data."""
    if isinstance(data, dict):
        for key in data:
            if key in _ENTITY_FIELDS:
                return key
    return ""


def _pagination_footer(data: dict) -> Optional[str]:
    """Return a one-line pagination summary if the response includes meta.pagination."""
    if not isinstance(data, dict):
        return None
    pagination = data.get("meta", {}).get("pagination", {})
    if not pagination:
        return None
    total = pagination.get("total")
    current = pagination.get("current_page")
    total_pages = pagination.get("total_pages")
    per_page = pagination.get("per_page")
    count = pagination.get("count")
    if total is None:
        return None
    if total_pages and total_pages > 1:
        return (
            f"(page {current}/{total_pages} — showing {count} of {total} total"
            f" — use --all to fetch everything)"
        )
    return f"({total} total)"


def format_output(
    data: Any,
    json_mode: bool = False,
    entity: str = "",
    fields: Optional[List[str]] = None,
) -> None:
    """Print data either as pretty JSON or as a human-readable table.

    Args:
        data: The API response payload (dict or list).
        json_mode: When True, output raw JSON.
        entity: Entity type hint (clients, invoices, …) for table formatting.
        fields: Optional list of field names to override defaults.
    """
    if json_mode:
        print(json.dumps(data, indent=2))
        return

    # Unwrap common InvoiceNinja response envelope shapes
    records: list[dict] = []
    _found_envelope = False
    if isinstance(data, list):
        records = data
        _found_envelope = True
    elif isinstance(data, dict):
        # Try common envelope keys — list response
        for key in (entity, "data"):
            if key and key in data and isinstance(data[key], list):
                records = data[key]
                _found_envelope = True
                if not entity:
                    entity = key
                break
        if not _found_envelope:
            # Single-record response
            for key in (entity, "data"):
                if key and key in data and isinstance(data[key], dict):
                    records = [data[key]]
                    _found_envelope = True
                    if not entity:
                        entity = key
                    break
        if not _found_envelope:
            # Last resort: print as JSON
            print(json.dumps(data, indent=2))
            return

    if not records:
        print("(no records)")
        return

    # Determine display fields
    if fields:
        display_fields = [(f, f) for f in fields]
    else:
        display_fields = _ENTITY_FIELDS.get(entity, [])
        if not display_fields:
            # Fallback: show first 6 keys of the first record
            sample = records[0] if records else {}
            display_fields = [(k, k) for k in list(sample.keys())[:6]]

    headers = [label for _, label in display_fields]
    rows = [_extract_row(r, display_fields, entity) for r in records]

    if _HAS_TABULATE:
        print(tabulate(rows, headers=headers, tablefmt="simple"))
    else:
        # Fallback plain text table
        col_widths = [max(len(str(h)), max((len(str(r[i])) for r in rows), default=0)) for i, h in enumerate(headers)]
        header_line = "  ".join(str(h).ljust(w) for h, w in zip(headers, col_widths))
        sep = "  ".join("-" * w for w in col_widths)
        print(header_line)
        print(sep)
        for row in rows:
            print("  ".join(str(v).ljust(w) for v, w in zip(row, col_widths)))

    footer = _pagination_footer(data) if isinstance(data, dict) else None
    if footer:
        print(footer)


def print_error(message: str) -> None:
    """Print a formatted error message to stderr."""
    import sys
    print(f"Error: {message}", file=sys.stderr)


def print_success(message: str) -> None:
    """Print a success message."""
    print(f"OK: {message}")
