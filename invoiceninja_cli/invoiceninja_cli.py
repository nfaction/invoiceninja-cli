"""Main CLI entry point for invoiceninja-cli.

Usage:
    invoiceninja-cli [OPTIONS] COMMAND [ARGS]...
"""

from __future__ import annotations

import sys
from typing import Optional

import click

from .utils.config import get_config, load_config, save_config, require_config
from .utils.output import format_output, print_error, print_success
from .core.session import InvoiceNinjaSession, InvoiceNinjaAPIError
from .core.clients import ClientResource
from .core.invoices import InvoiceResource
from .core.quotes import QuoteResource
from .core.payments import PaymentResource
from .core.products import ProductResource
from .core.projects import ProjectResource
from .core.tasks import TaskResource
from .core.vendors import VendorResource
from .core.expenses import ExpenseResource
from .core.credits import CreditResource
from .core.recurring_invoices import RecurringInvoiceResource
from .core.purchase_orders import PurchaseOrderResource


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_local_network_error(exc: Exception) -> bool:
    return "No route to host" in str(exc) or "Errno 65" in str(exc)


def _trigger_local_network_permission() -> bool:
    """Send an mDNS multicast probe to trigger the macOS Local Network permission dialog.

    Returns True if the probe was sent without an immediate socket error (not a guarantee
    the dialog appeared — macOS may silently suppress it if already denied).
    """
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.settimeout(0.5)
        sock.sendto(b"\x00" * 12, ("224.0.0.251", 5353))
        sock.close()
        return True
    except Exception:
        return False


def _make_session() -> InvoiceNinjaSession:
    """Build an authenticated session from stored/env config."""
    try:
        config = require_config()
    except RuntimeError as exc:
        print_error(str(exc))
        sys.exit(1)
    return InvoiceNinjaSession(config["url"], config["token"])


def _handle_api(func, *args, json_mode: bool = False, entity: str = "",
                all_pages: bool = False, **kwargs):
    """Call an API function and handle errors + output formatting."""
    try:
        if all_pages:
            result = func(*args, all_pages=True, **kwargs)
        else:
            result = func(*args, **kwargs)
        format_output(result, json_mode=json_mode, entity=entity)
    except InvoiceNinjaAPIError as exc:
        print_error(str(exc))
        sys.exit(1)
    except Exception as exc:
        import platform
        if _is_local_network_error(exc) and platform.system() == "Darwin":
            _trigger_local_network_permission()
            click.echo(
                "macOS is blocking Python's access to your local network.\n"
                "Reset the permission so macOS will prompt you to allow it:\n\n"
                "  tccutil reset LocalNetwork\n\n"
                "Then run this command again and approve the dialog."
            )
            sys.exit(1)
        print_error(f"Connection failed: {exc}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Common options
# ---------------------------------------------------------------------------

_json_option = click.option(
    "--json", "json_mode", is_flag=True, default=False,
    help="Output raw JSON instead of a table."
)
_page_option = click.option(
    "--page", default=1, show_default=True, type=int, help="Page number."
)
_per_page_option = click.option(
    "--per-page", default=20, show_default=True, type=int, help="Records per page."
)
_filter_option = click.option(
    "--filter", "filter_text", default=None, help="Full-text filter string."
)
_all_option = click.option(
    "--all", "all_pages", is_flag=True, default=False,
    help="Fetch all pages automatically (ignores --page/--per-page).",
)


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(version="0.1.0", prog_name="invoiceninja-cli")
def cli():
    """InvoiceNinja v5 CLI — manage your self-hosted InvoiceNinja instance."""


# ---------------------------------------------------------------------------
# configure
# ---------------------------------------------------------------------------

@cli.command()
def configure():
    """Interactively set URL and API token."""
    existing = load_config()
    url = click.prompt(
        "InvoiceNinja base URL",
        default=existing.get("url", ""),
    )
    token = click.prompt(
        "API token",
        default=existing.get("token", ""),
        hide_input=True,
    )
    company_id = click.prompt(
        "Company ID (optional, press Enter to skip)",
        default=existing.get("company_id", ""),
    )
    config = {"url": url.rstrip("/"), "token": token}
    if company_id:
        config["company_id"] = company_id
    save_config(config)
    print_success("Configuration saved.")


# ---------------------------------------------------------------------------
# ping
# ---------------------------------------------------------------------------

@cli.command()
@_json_option
def ping(json_mode: bool):
    """Test the connection to InvoiceNinja."""
    session = _make_session()
    try:
        result = session.ping()
        if json_mode:
            format_output(result, json_mode=True)
        else:
            click.echo("Connection successful.")
    except InvoiceNinjaAPIError as exc:
        print_error(str(exc))
        sys.exit(1)
    except Exception as exc:
        import platform
        if _is_local_network_error(exc) and platform.system() == "Darwin":
            _trigger_local_network_permission()
            click.echo(
                "macOS needs Local Network permission for Python.\n"
                "A permission dialog should have appeared — approve it, then press Enter to retry."
            )
            click.pause("")
            try:
                result = session.ping()
                if json_mode:
                    format_output(result, json_mode=True)
                else:
                    click.echo("Connection successful.")
                return
            except Exception as retry_exc:
                print_error(f"Connection failed after permission grant: {retry_exc}")
                sys.exit(1)
        print_error(f"Connection failed: {exc}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# clients
# ---------------------------------------------------------------------------

@cli.group()
def clients():
    """Manage clients."""


@clients.command("list")
@_json_option
@_page_option
@_per_page_option
@_filter_option
@click.option("--status", default=None, help="Filter by client status.")
@_all_option
def clients_list(json_mode, page, per_page, filter_text, status, all_pages):
    """List clients."""
    res = ClientResource(_make_session())
    _handle_api(res.list, page=page, per_page=per_page, filter=filter_text,
                status=status, json_mode=json_mode, entity="clients", all_pages=all_pages)


@clients.command("get")
@click.argument("id")
@_json_option
def clients_get(id, json_mode):
    """Get a client by ID."""
    res = ClientResource(_make_session())
    _handle_api(res.get, id, json_mode=json_mode, entity="clients")


@clients.command("create")
@click.option("--name", required=True, help="Client name.")
@click.option("--email", default=None, help="Primary contact email.")
@click.option("--phone", default=None, help="Phone number.")
@click.option("--address1", default=None, help="Street address.")
@click.option("--city", default=None, help="City.")
@click.option("--state", default=None, help="State / province.")
@click.option("--country-id", default=None, help="Country ID.")
@click.option("--vat-number", default=None, help="VAT / tax number.")
@_json_option
def clients_create(name, email, phone, address1, city, state, country_id, vat_number, json_mode):
    """Create a new client."""
    data: dict = {"name": name}
    contacts = {}
    if email:
        contacts["email"] = email
    if phone:
        contacts["phone"] = phone
    if contacts:
        data["contacts"] = [contacts]
    if address1:
        data["address1"] = address1
    if city:
        data["city"] = city
    if state:
        data["state"] = state
    if country_id:
        data["country_id"] = country_id
    if vat_number:
        data["vat_number"] = vat_number

    res = ClientResource(_make_session())
    _handle_api(res.create, data, json_mode=json_mode, entity="clients")


@clients.command("update")
@click.argument("id")
@click.option("--name", default=None)
@click.option("--email", default=None)
@click.option("--phone", default=None)
@click.option("--address1", default=None)
@click.option("--city", default=None)
@click.option("--state", default=None)
@_json_option
def clients_update(id, name, email, phone, address1, city, state, json_mode):
    """Update a client by ID."""
    data: dict = {}
    if name:
        data["name"] = name
    if email or phone:
        contacts = {}
        if email:
            contacts["email"] = email
        if phone:
            contacts["phone"] = phone
        data["contacts"] = [contacts]
    if address1:
        data["address1"] = address1
    if city:
        data["city"] = city
    if state:
        data["state"] = state
    if not data:
        print_error("No fields to update.")
        sys.exit(1)
    res = ClientResource(_make_session())
    _handle_api(res.update, id, data, json_mode=json_mode, entity="clients")


@clients.command("delete")
@click.argument("id")
def clients_delete(id):
    """Delete a client by ID."""
    if not click.confirm(f"Delete client {id}?"):
        return
    res = ClientResource(_make_session())
    _handle_api(res.delete, id, entity="clients")


@clients.command("archive")
@click.argument("ids", nargs=-1, required=True)
@_json_option
def clients_archive(ids, json_mode):
    """Archive one or more clients."""
    res = ClientResource(_make_session())
    _handle_api(res.archive, list(ids), json_mode=json_mode, entity="clients")


@clients.command("restore")
@click.argument("ids", nargs=-1, required=True)
@_json_option
def clients_restore(ids, json_mode):
    """Restore one or more archived clients."""
    res = ClientResource(_make_session())
    _handle_api(res.restore, list(ids), json_mode=json_mode, entity="clients")


# ---------------------------------------------------------------------------
# invoices
# ---------------------------------------------------------------------------

@cli.group()
def invoices():
    """Manage invoices."""


@invoices.command("list")
@_json_option
@_page_option
@_per_page_option
@_filter_option
@click.option("--status", "client_status", default=None,
              type=click.Choice(["paid", "unpaid", "overdue", "draft", "sent"],
                                case_sensitive=False),
              help="Filter by invoice status.")
@click.option("--client-id", default=None, help="Filter by client ID.")
@click.option("--number", default=None, help="Filter by invoice number.")
@_all_option
def invoices_list(json_mode, page, per_page, filter_text, client_status, client_id, number, all_pages):
    """List invoices."""
    res = InvoiceResource(_make_session())
    _handle_api(res.list, page=page, per_page=per_page, filter=filter_text,
                client_status=client_status, client_id=client_id, number=number,
                json_mode=json_mode, entity="invoices", all_pages=all_pages)


@invoices.command("get")
@click.argument("id")
@_json_option
def invoices_get(id, json_mode):
    """Get an invoice by ID."""
    res = InvoiceResource(_make_session())
    _handle_api(res.get, id, json_mode=json_mode, entity="invoices")


def _build_line_items(
    item_key: tuple,
    item_qty: tuple,
    item_cost: tuple,
    item_notes: tuple,
    item_type: tuple,
    task_ids: tuple,
) -> list:
    """Build a list of line_item dicts from parallel repeatable CLI options.

    Product/service items come from --item-key/--item-qty/--item-cost/--item-notes/--item-type.
    Task items come from --task-id (one entry per task ID, type_id=4).
    The two sets are combined in the order: product items first, then task items.
    """
    _TYPE_MAP = {"product": "1", "service": "2", "unpaid-time": "3", "paid-time": "4"}
    items = []

    # Zip product/service items — missing trailing values default to sensible fallbacks
    max_len = max(len(item_key), len(item_qty), len(item_cost), len(item_notes), len(item_type), 1) if any(
        [item_key, item_qty, item_cost, item_notes, item_type]
    ) else 0
    for i in range(max_len):
        key = item_key[i] if i < len(item_key) else ""
        qty = item_qty[i] if i < len(item_qty) else 1.0
        cost = item_cost[i] if i < len(item_cost) else 0.0
        notes = item_notes[i] if i < len(item_notes) else ""
        type_str = item_type[i] if i < len(item_type) else "product"
        items.append({
            "product_key": key,
            "quantity": qty,
            "cost": cost,
            "notes": notes,
            "type_id": _TYPE_MAP.get(type_str, "1"),
        })

    # Task items
    for tid in task_ids:
        items.append({
            "task_id": tid,
            "type_id": "4",  # paid time
            "quantity": 1,
            "cost": 0,
            "notes": "",
            "product_key": "",
        })

    return items


# Repeatable line-item options shared by create and update
_item_key_option = click.option(
    "--item-key", "item_key", multiple=True,
    help="Product key / SKU (repeatable, one per line item).",
)
_item_qty_option = click.option(
    "--item-qty", "item_qty", multiple=True, type=float,
    help="Quantity for this line item (repeatable).",
)
_item_cost_option = click.option(
    "--item-cost", "item_cost", multiple=True, type=float,
    help="Unit cost for this line item (repeatable).",
)
_item_notes_option = click.option(
    "--item-notes", "item_notes", multiple=True,
    help="Description / notes for this line item (repeatable).",
)
_item_type_option = click.option(
    "--item-type", "item_type", multiple=True,
    type=click.Choice(["product", "service", "unpaid-time", "paid-time"], case_sensitive=False),
    help="Line item type (repeatable). Default: product.",
)
_task_id_option = click.option(
    "--task-id", "task_ids", multiple=True,
    help="Task ID to attach as a line item (repeatable).",
)


@invoices.command("create")
@click.option("--client-id", required=True, help="Client ID.")
@click.option("--amount", type=float, default=None,
              help="Shorthand: create a single line item with this total. Ignored if --item-* flags are used.")
@click.option("--date", "invoice_date", default=None, help="Invoice date (YYYY-MM-DD).")
@click.option("--due-date", default=None, help="Due date (YYYY-MM-DD).")
@click.option("--po-number", default=None, help="Purchase order number.")
@click.option("--notes", default=None, help="Public notes.")
@_item_key_option
@_item_qty_option
@_item_cost_option
@_item_notes_option
@_item_type_option
@_task_id_option
@_json_option
def invoices_create(
    client_id, amount, invoice_date, due_date, po_number, notes,
    item_key, item_qty, item_cost, item_notes, item_type, task_ids,
    json_mode,
):
    """Create a new invoice.

    Line items can be specified two ways:

    \b
    Simple (one total amount):
      --amount 1500

    \b
    Detailed (repeatable --item-* flags, one set per line item):
      --item-key CONSULT --item-qty 10 --item-cost 150 --item-notes "Oct consulting"
      --item-key EXPENSES --item-qty 1 --item-cost 200 --item-notes "Travel"

    \b
    Attach a task as a line item:
      --task-id abc123def
    """
    data: dict = {"client_id": client_id}
    if invoice_date:
        data["date"] = invoice_date
    if due_date:
        data["due_date"] = due_date
    if po_number:
        data["po_number"] = po_number
    if notes:
        data["public_notes"] = notes

    if item_key or item_qty or item_cost or item_notes or item_type or task_ids:
        data["line_items"] = _build_line_items(item_key, item_qty, item_cost, item_notes, item_type, task_ids)
    elif amount is not None:
        data["line_items"] = [{"quantity": 1, "cost": amount, "product_key": "Service"}]

    res = InvoiceResource(_make_session())
    _handle_api(res.create, data, json_mode=json_mode, entity="invoices")


@invoices.command("update")
@click.argument("id")
@click.option("--client-id", default=None)
@click.option("--date", "invoice_date", default=None)
@click.option("--due-date", default=None)
@click.option("--po-number", default=None)
@click.option("--notes", default=None)
@_item_key_option
@_item_qty_option
@_item_cost_option
@_item_notes_option
@_item_type_option
@_task_id_option
@_json_option
def invoices_update(
    id, client_id, invoice_date, due_date, po_number, notes,
    item_key, item_qty, item_cost, item_notes, item_type, task_ids,
    json_mode,
):
    """Update an invoice by ID.

    Pass --item-* flags to replace ALL line items on the invoice.
    Use 'invoices add-item' or 'invoices remove-item' to modify individual items.
    """
    data: dict = {}
    if client_id:
        data["client_id"] = client_id
    if invoice_date:
        data["date"] = invoice_date
    if due_date:
        data["due_date"] = due_date
    if po_number:
        data["po_number"] = po_number
    if notes:
        data["public_notes"] = notes
    if item_key or item_qty or item_cost or item_notes or item_type or task_ids:
        data["line_items"] = _build_line_items(item_key, item_qty, item_cost, item_notes, item_type, task_ids)
    if not data:
        print_error("No fields to update.")
        sys.exit(1)
    res = InvoiceResource(_make_session())
    _handle_api(res.update, id, data, json_mode=json_mode, entity="invoices")


_TYPE_LABELS = {"1": "Product", "2": "Service", "3": "Unpaid time", "4": "Paid time"}
_TYPE_REVERSE = {v: k for k, v in _TYPE_LABELS.items()}
_TYPE_CLI_MAP = {"product": "1", "service": "2", "unpaid-time": "3", "paid-time": "4"}
_TYPE_CLI_REVERSE = {v: k for k, v in _TYPE_CLI_MAP.items()}


def _print_items_table(items: list) -> None:
    """Render line items as a table to stdout."""
    from tabulate import tabulate
    rows = []
    for i, item in enumerate(items):
        qty = item.get("quantity", 1) or 1
        cost = item.get("cost", 0) or 0
        total = round(float(qty) * float(cost), 2)
        notes = item.get("notes", "") or ""
        # Wrap long notes at 45 chars without cutting words
        if len(notes) > 45:
            notes = notes[:44].rsplit(" ", 1)[0] + "…"
        rows.append([
            i,
            item.get("product_key", "") or "",
            notes,
            qty,
            cost,
            total,
            _TYPE_LABELS.get(str(item.get("type_id", "1")), "Product"),
            item.get("task_id", "") or "",
        ])
    click.echo(tabulate(
        rows,
        headers=["#", "Key", "Notes", "Qty", "Unit cost", "Total", "Type", "Task ID"],
        tablefmt="simple",
        floatfmt=".2f",
    ))


def _fetch_invoice_items(res: "InvoiceResource", invoice_id: str):
    """Fetch an invoice and return (raw_invoice_dict, line_items_list)."""
    try:
        invoice = res.get(invoice_id)
    except InvoiceNinjaAPIError as exc:
        print_error(str(exc))
        sys.exit(1)
    record = invoice.get("data", invoice)
    return record, list(record.get("line_items", []))


@invoices.command("items")
@click.argument("id")
@_json_option
def invoices_items(id, json_mode):
    """List line items on an invoice with indices and line totals.

    Use the index shown here with 'invoices edit-item' or 'invoices remove-item'.
    """
    res = InvoiceResource(_make_session())
    _, items = _fetch_invoice_items(res, id)

    if json_mode:
        import json as _json
        click.echo(_json.dumps(items, indent=2))
        return

    if not items:
        click.echo("No line items on this invoice.")
        return

    _print_items_table(items)


@invoices.command("add-item")
@click.argument("id")
@click.option("--product-key", default="", help="Product key / SKU.")
@click.option("--qty", type=float, default=1.0, show_default=True, help="Quantity.")
@click.option("--cost", type=float, required=True, help="Unit cost.")
@click.option("--notes", default="", help="Line item description.")
@click.option("--type", "item_type",
              type=click.Choice(["product", "service", "unpaid-time", "paid-time"], case_sensitive=False),
              default="product", show_default=True, help="Line item type.")
@_json_option
def invoices_add_item(id, product_key, qty, cost, notes, item_type, json_mode):
    """Append a product or service line item to an existing invoice."""
    res = InvoiceResource(_make_session())
    _, items = _fetch_invoice_items(res, id)
    items.append({
        "product_key": product_key,
        "quantity": qty,
        "cost": cost,
        "notes": notes,
        "type_id": _TYPE_CLI_MAP.get(item_type, "1"),
    })
    _handle_api(res.update, id, {"line_items": items}, json_mode=json_mode, entity="invoices")
    if not json_mode:
        print_success(f"Line item added (invoice now has {len(items)} item(s)).")


@invoices.command("add-task")
@click.argument("id")
@click.option("--task-id", required=True, help="Task ID to attach.")
@click.option("--cost", type=float, default=0.0, show_default=True, help="Rate override (0 = use task rate).")
@click.option("--notes", default="", help="Optional description override.")
@_json_option
def invoices_add_task(id, task_id, cost, notes, json_mode):
    """Append a task as a paid-time line item on an existing invoice."""
    res = InvoiceResource(_make_session())
    _, items = _fetch_invoice_items(res, id)
    items.append({
        "task_id": task_id,
        "type_id": "4",
        "quantity": 1,
        "cost": cost,
        "notes": notes,
        "product_key": "",
    })
    _handle_api(res.update, id, {"line_items": items}, json_mode=json_mode, entity="invoices")
    if not json_mode:
        print_success(f"Task {task_id} attached (invoice now has {len(items)} item(s)).")


@invoices.command("edit-item")
@click.argument("id")
@click.option("--index", type=int, default=None,
              help="Zero-based index of the item to edit. Omit to select interactively.")
@click.option("--product-key", default=None, help="New product key / SKU.")
@click.option("--qty", type=float, default=None, help="New quantity.")
@click.option("--cost", type=float, default=None, help="New unit cost.")
@click.option("--notes", default=None, help="New description / notes.")
@click.option("--type", "item_type",
              type=click.Choice(["product", "service", "unpaid-time", "paid-time"], case_sensitive=False),
              default=None, help="New line item type.")
@click.option("--task-id", default=None, help="New task ID (task items only).")
@_json_option
def invoices_edit_item(id, index, product_key, qty, cost, notes, item_type, task_id, json_mode):
    """Edit a single line item on an invoice.

    \b
    Interactive (recommended) — omit --index to pick from a list:
      invoices edit-item INVOICE_ID

    \b
    Non-interactive — supply --index and any fields to change:
      invoices edit-item INVOICE_ID --index 1 --cost 200 --notes "Updated desc"

    Only the fields you pass are changed; everything else is preserved.
    """
    res = InvoiceResource(_make_session())
    _, items = _fetch_invoice_items(res, id)

    if not items:
        print_error("This invoice has no line items to edit.")
        sys.exit(1)

    # ── Step 1: resolve index ──────────────────────────────────────────────
    if index is None:
        # Interactive selection: show table then prompt
        click.echo(f"\nLine items on invoice {id}:\n")
        _print_items_table(items)
        click.echo()
        index = click.prompt(
            f"Select item to edit [0–{len(items) - 1}]",
            type=click.IntRange(0, len(items) - 1),
        )

    if index < 0 or index >= len(items):
        print_error(f"Index {index} out of range — invoice has {len(items)} item(s) (0–{len(items)-1}).")
        sys.exit(1)

    item = dict(items[index])  # shallow copy so we can mutate safely

    # ── Step 2: apply changes ──────────────────────────────────────────────
    non_interactive = any(v is not None for v in [product_key, qty, cost, notes, item_type, task_id])

    if non_interactive:
        # Apply only the flags that were explicitly passed
        if product_key is not None:
            item["product_key"] = product_key
        if qty is not None:
            item["quantity"] = qty
        if cost is not None:
            item["cost"] = cost
        if notes is not None:
            item["notes"] = notes
        if item_type is not None:
            item["type_id"] = _TYPE_CLI_MAP[item_type]
        if task_id is not None:
            item["task_id"] = task_id
    else:
        # Interactive field-by-field prompts with current values as defaults
        current_type_cli = _TYPE_CLI_REVERSE.get(str(item.get("type_id", "1")), "product")

        click.echo(f"\nEditing item #{index}  (press Enter to keep current value)\n")

        item["product_key"] = click.prompt(
            "  Product key", default=item.get("product_key", "") or "", show_default=True
        )
        item["notes"] = click.prompt(
            "  Notes / description", default=item.get("notes", "") or "", show_default=True
        )
        item["quantity"] = click.prompt(
            "  Quantity", default=float(item.get("quantity", 1) or 1),
            type=float, show_default=True
        )
        item["cost"] = click.prompt(
            "  Unit cost", default=float(item.get("cost", 0) or 0),
            type=float, show_default=True
        )
        new_type = click.prompt(
            "  Type",
            default=current_type_cli,
            type=click.Choice(["product", "service", "unpaid-time", "paid-time"],
                              case_sensitive=False),
            show_default=True,
        )
        item["type_id"] = _TYPE_CLI_MAP[new_type]

        # Only prompt for task_id on task-type items
        if new_type in ("unpaid-time", "paid-time"):
            item["task_id"] = click.prompt(
                "  Task ID", default=item.get("task_id", "") or "", show_default=True
            )

        # Preview the edited item before saving
        click.echo("\nUpdated item:\n")
        _print_items_table([item])
        click.echo()
        if not click.confirm("Save changes?", default=True):
            click.echo("Aborted — no changes saved.")
            return

    # ── Step 3: PUT the updated line items ─────────────────────────────────
    items[index] = item
    _handle_api(res.update, id, {"line_items": items}, json_mode=json_mode, entity="invoices")
    if not json_mode:
        label = item.get("product_key") or item.get("task_id") or f"item #{index}"
        print_success(f"Item '{label}' updated.")


@invoices.command("remove-item")
@click.argument("id")
@click.option("--index", type=int, required=True, help="Zero-based index of the line item to remove (see 'invoices items').")
@_json_option
def invoices_remove_item(id, index, json_mode):
    """Remove a line item from an invoice by its index.

    Run 'invoices items ID' first to see item indices.
    """
    res = InvoiceResource(_make_session())
    _, items = _fetch_invoice_items(res, id)

    if index < 0 or index >= len(items):
        print_error(f"Index {index} out of range — invoice has {len(items)} item(s) (0–{len(items)-1}).")
        sys.exit(1)

    removed = items.pop(index)
    _handle_api(res.update, id, {"line_items": items}, json_mode=json_mode, entity="invoices")
    if not json_mode:
        label = removed.get("product_key") or removed.get("task_id") or f"item #{index}"
        print_success(f"Removed '{label}' (invoice now has {len(items)} item(s)).")


@invoices.command("delete")
@click.argument("id")
def invoices_delete(id):
    """Delete an invoice by ID."""
    if not click.confirm(f"Delete invoice {id}?"):
        return
    res = InvoiceResource(_make_session())
    _handle_api(res.delete, id, entity="invoices")


@invoices.command("send")
@click.argument("id")
@_json_option
def invoices_send(id, json_mode):
    """Email an invoice to the client."""
    res = InvoiceResource(_make_session())
    _handle_api(res.send, id, json_mode=json_mode, entity="invoices")
    if not json_mode:
        print_success(f"Invoice {id} emailed.")


@invoices.command("mark-paid")
@click.argument("id")
@_json_option
def invoices_mark_paid(id, json_mode):
    """Mark an invoice as paid."""
    res = InvoiceResource(_make_session())
    _handle_api(res.mark_paid, id, json_mode=json_mode, entity="invoices")
    if not json_mode:
        print_success(f"Invoice {id} marked as paid.")


@invoices.command("archive")
@click.argument("ids", nargs=-1, required=True)
@_json_option
def invoices_archive(ids, json_mode):
    """Archive one or more invoices."""
    res = InvoiceResource(_make_session())
    _handle_api(res.archive, list(ids), json_mode=json_mode, entity="invoices")


@invoices.command("restore")
@click.argument("ids", nargs=-1, required=True)
@_json_option
def invoices_restore(ids, json_mode):
    """Restore one or more archived invoices."""
    res = InvoiceResource(_make_session())
    _handle_api(res.restore, list(ids), json_mode=json_mode, entity="invoices")


# ---------------------------------------------------------------------------
# quotes
# ---------------------------------------------------------------------------

@cli.group()
def quotes():
    """Manage quotes."""


@quotes.command("list")
@_json_option
@_page_option
@_per_page_option
@_filter_option
@click.option("--client-id", default=None)
@click.option("--status", "client_status", default=None)
@_all_option
def quotes_list(json_mode, page, per_page, filter_text, client_id, client_status, all_pages):
    """List quotes."""
    res = QuoteResource(_make_session())
    _handle_api(res.list, page=page, per_page=per_page, filter=filter_text,
                client_id=client_id, client_status=client_status,
                json_mode=json_mode, entity="quotes", all_pages=all_pages)


@quotes.command("get")
@click.argument("id")
@_json_option
def quotes_get(id, json_mode):
    """Get a quote by ID."""
    res = QuoteResource(_make_session())
    _handle_api(res.get, id, json_mode=json_mode, entity="quotes")


@quotes.command("create")
@click.option("--client-id", required=True)
@click.option("--amount", type=float, default=None)
@click.option("--date", "quote_date", default=None)
@click.option("--valid-until", default=None)
@click.option("--notes", default=None)
@_json_option
def quotes_create(client_id, amount, quote_date, valid_until, notes, json_mode):
    """Create a new quote."""
    data: dict = {"client_id": client_id}
    if quote_date:
        data["date"] = quote_date
    if valid_until:
        data["valid_until"] = valid_until
    if notes:
        data["public_notes"] = notes
    if amount is not None:
        data["line_items"] = [{"quantity": 1, "cost": amount, "product_key": "Service"}]
    res = QuoteResource(_make_session())
    _handle_api(res.create, data, json_mode=json_mode, entity="quotes")


@quotes.command("update")
@click.argument("id")
@click.option("--client-id", default=None)
@click.option("--date", "quote_date", default=None)
@click.option("--valid-until", default=None)
@click.option("--notes", default=None)
@_json_option
def quotes_update(id, client_id, quote_date, valid_until, notes, json_mode):
    """Update a quote by ID."""
    data: dict = {}
    if client_id:
        data["client_id"] = client_id
    if quote_date:
        data["date"] = quote_date
    if valid_until:
        data["valid_until"] = valid_until
    if notes:
        data["public_notes"] = notes
    if not data:
        print_error("No fields to update.")
        sys.exit(1)
    res = QuoteResource(_make_session())
    _handle_api(res.update, id, data, json_mode=json_mode, entity="quotes")


@quotes.command("delete")
@click.argument("id")
def quotes_delete(id):
    """Delete a quote by ID."""
    if not click.confirm(f"Delete quote {id}?"):
        return
    res = QuoteResource(_make_session())
    _handle_api(res.delete, id, entity="quotes")


@quotes.command("approve")
@click.argument("id")
@_json_option
def quotes_approve(id, json_mode):
    """Approve a quote."""
    res = QuoteResource(_make_session())
    _handle_api(res.approve, id, json_mode=json_mode, entity="quotes")
    if not json_mode:
        print_success(f"Quote {id} approved.")


@quotes.command("send")
@click.argument("id")
@_json_option
def quotes_send(id, json_mode):
    """Email a quote to the client."""
    res = QuoteResource(_make_session())
    _handle_api(res.send, id, json_mode=json_mode, entity="quotes")
    if not json_mode:
        print_success(f"Quote {id} emailed.")


@quotes.command("archive")
@click.argument("ids", nargs=-1, required=True)
@_json_option
def quotes_archive(ids, json_mode):
    """Archive one or more quotes."""
    res = QuoteResource(_make_session())
    _handle_api(res.archive, list(ids), json_mode=json_mode, entity="quotes")


@quotes.command("restore")
@click.argument("ids", nargs=-1, required=True)
@_json_option
def quotes_restore(ids, json_mode):
    """Restore one or more archived quotes."""
    res = QuoteResource(_make_session())
    _handle_api(res.restore, list(ids), json_mode=json_mode, entity="quotes")


# ---------------------------------------------------------------------------
# payments
# ---------------------------------------------------------------------------

@cli.group()
def payments():
    """Manage payments."""


@payments.command("list")
@_json_option
@_page_option
@_per_page_option
@_filter_option
@click.option("--client-id", default=None)
@_all_option
def payments_list(json_mode, page, per_page, filter_text, client_id, all_pages):
    """List payments."""
    res = PaymentResource(_make_session())
    _handle_api(res.list, page=page, per_page=per_page, filter=filter_text,
                client_id=client_id, json_mode=json_mode, entity="payments", all_pages=all_pages)


@payments.command("get")
@click.argument("id")
@_json_option
def payments_get(id, json_mode):
    """Get a payment by ID."""
    res = PaymentResource(_make_session())
    _handle_api(res.get, id, json_mode=json_mode, entity="payments")


@payments.command("create")
@click.option("--client-id", required=True, help="Client ID.")
@click.option("--invoice-id", default=None, help="Invoice ID to apply payment to.")
@click.option("--amount", required=True, type=float, help="Payment amount.")
@click.option("--date", "payment_date", default=None, help="Payment date (YYYY-MM-DD).")
@click.option("--type-id", default="1", help="Payment type ID (1=Bank Transfer, 4=Credit Card…).")
@_json_option
def payments_create(client_id, invoice_id, amount, payment_date, type_id, json_mode):
    """Record a payment."""
    data: dict = {
        "client_id": client_id,
        "amount": amount,
        "type_id": type_id,
    }
    if payment_date:
        data["date"] = payment_date
    if invoice_id:
        data["invoices"] = [{"invoice_id": invoice_id, "amount": amount}]
    res = PaymentResource(_make_session())
    _handle_api(res.create, data, json_mode=json_mode, entity="payments")


@payments.command("update")
@click.argument("id")
@click.option("--amount", type=float, default=None)
@click.option("--date", "payment_date", default=None)
@_json_option
def payments_update(id, amount, payment_date, json_mode):
    """Update a payment by ID."""
    data: dict = {}
    if amount is not None:
        data["amount"] = amount
    if payment_date:
        data["date"] = payment_date
    if not data:
        print_error("No fields to update.")
        sys.exit(1)
    res = PaymentResource(_make_session())
    _handle_api(res.update, id, data, json_mode=json_mode, entity="payments")


@payments.command("delete")
@click.argument("id")
def payments_delete(id):
    """Delete a payment by ID."""
    if not click.confirm(f"Delete payment {id}?"):
        return
    res = PaymentResource(_make_session())
    _handle_api(res.delete, id, entity="payments")


@payments.command("archive")
@click.argument("ids", nargs=-1, required=True)
@_json_option
def payments_archive(ids, json_mode):
    """Archive one or more payments."""
    res = PaymentResource(_make_session())
    _handle_api(res.archive, list(ids), json_mode=json_mode, entity="payments")


@payments.command("restore")
@click.argument("ids", nargs=-1, required=True)
@_json_option
def payments_restore(ids, json_mode):
    """Restore one or more archived payments."""
    res = PaymentResource(_make_session())
    _handle_api(res.restore, list(ids), json_mode=json_mode, entity="payments")


# ---------------------------------------------------------------------------
# products
# ---------------------------------------------------------------------------

@cli.group()
def products():
    """Manage products."""


@products.command("list")
@_json_option
@_page_option
@_per_page_option
@_filter_option
@_all_option
def products_list(json_mode, page, per_page, filter_text, all_pages):
    """List products."""
    res = ProductResource(_make_session())
    _handle_api(res.list, page=page, per_page=per_page, filter=filter_text,
                json_mode=json_mode, entity="products", all_pages=all_pages)


@products.command("get")
@click.argument("id")
@_json_option
def products_get(id, json_mode):
    """Get a product by ID."""
    res = ProductResource(_make_session())
    _handle_api(res.get, id, json_mode=json_mode, entity="products")


@products.command("create")
@click.option("--key", "product_key", required=True, help="Product key / SKU.")
@click.option("--price", type=float, required=True, help="Unit price.")
@click.option("--notes", default=None, help="Product description.")
@click.option("--quantity", type=float, default=1.0, show_default=True, help="Default quantity.")
@_json_option
def products_create(product_key, price, notes, quantity, json_mode):
    """Create a new product."""
    data: dict = {"product_key": product_key, "price": price, "quantity": quantity}
    if notes:
        data["notes"] = notes
    res = ProductResource(_make_session())
    _handle_api(res.create, data, json_mode=json_mode, entity="products")


@products.command("update")
@click.argument("id")
@click.option("--key", "product_key", default=None)
@click.option("--price", type=float, default=None)
@click.option("--notes", default=None)
@click.option("--quantity", type=float, default=None)
@_json_option
def products_update(id, product_key, price, notes, quantity, json_mode):
    """Update a product by ID."""
    data: dict = {}
    if product_key:
        data["product_key"] = product_key
    if price is not None:
        data["price"] = price
    if notes:
        data["notes"] = notes
    if quantity is not None:
        data["quantity"] = quantity
    if not data:
        print_error("No fields to update.")
        sys.exit(1)
    res = ProductResource(_make_session())
    _handle_api(res.update, id, data, json_mode=json_mode, entity="products")


@products.command("delete")
@click.argument("id")
def products_delete(id):
    """Delete a product by ID."""
    if not click.confirm(f"Delete product {id}?"):
        return
    res = ProductResource(_make_session())
    _handle_api(res.delete, id, entity="products")


@products.command("archive")
@click.argument("ids", nargs=-1, required=True)
@_json_option
def products_archive(ids, json_mode):
    """Archive one or more products."""
    res = ProductResource(_make_session())
    _handle_api(res.archive, list(ids), json_mode=json_mode, entity="products")


@products.command("restore")
@click.argument("ids", nargs=-1, required=True)
@_json_option
def products_restore(ids, json_mode):
    """Restore one or more archived products."""
    res = ProductResource(_make_session())
    _handle_api(res.restore, list(ids), json_mode=json_mode, entity="products")


# ---------------------------------------------------------------------------
# tasks
# ---------------------------------------------------------------------------

@cli.group()
def tasks():
    """Manage tasks."""


@tasks.command("list")
@_json_option
@_page_option
@_per_page_option
@_filter_option
@click.option("--client-id", default=None)
@click.option("--project-id", default=None)
@_all_option
def tasks_list(json_mode, page, per_page, filter_text, client_id, project_id, all_pages):
    """List tasks."""
    res = TaskResource(_make_session())
    _handle_api(res.list, page=page, per_page=per_page, filter=filter_text,
                client_id=client_id, project_id=project_id,
                json_mode=json_mode, entity="tasks", all_pages=all_pages)


@tasks.command("get")
@click.argument("id")
@_json_option
def tasks_get(id, json_mode):
    """Get a task by ID."""
    res = TaskResource(_make_session())
    _handle_api(res.get, id, json_mode=json_mode, entity="tasks")


@tasks.command("create")
@click.option("--description", required=True, help="Task description.")
@click.option("--client-id", default=None, help="Client ID.")
@click.option("--project-id", default=None, help="Project ID.")
@_json_option
def tasks_create(description, client_id, project_id, json_mode):
    """Create a new task."""
    data: dict = {"description": description}
    if client_id:
        data["client_id"] = client_id
    if project_id:
        data["project_id"] = project_id
    res = TaskResource(_make_session())
    _handle_api(res.create, data, json_mode=json_mode, entity="tasks")


@tasks.command("update")
@click.argument("id")
@click.option("--description", default=None)
@click.option("--client-id", default=None)
@click.option("--project-id", default=None)
@_json_option
def tasks_update(id, description, client_id, project_id, json_mode):
    """Update a task by ID."""
    data: dict = {}
    if description:
        data["description"] = description
    if client_id:
        data["client_id"] = client_id
    if project_id:
        data["project_id"] = project_id
    if not data:
        print_error("No fields to update.")
        sys.exit(1)
    res = TaskResource(_make_session())
    _handle_api(res.update, id, data, json_mode=json_mode, entity="tasks")


@tasks.command("delete")
@click.argument("id")
def tasks_delete(id):
    """Delete a task by ID."""
    if not click.confirm(f"Delete task {id}?"):
        return
    res = TaskResource(_make_session())
    _handle_api(res.delete, id, entity="tasks")


@tasks.command("archive")
@click.argument("ids", nargs=-1, required=True)
@_json_option
def tasks_archive(ids, json_mode):
    """Archive one or more tasks."""
    res = TaskResource(_make_session())
    _handle_api(res.archive, list(ids), json_mode=json_mode, entity="tasks")


@tasks.command("restore")
@click.argument("ids", nargs=-1, required=True)
@_json_option
def tasks_restore(ids, json_mode):
    """Restore one or more archived tasks."""
    res = TaskResource(_make_session())
    _handle_api(res.restore, list(ids), json_mode=json_mode, entity="tasks")


@tasks.command("start")
@click.argument("id")
@_json_option
def tasks_start(id, json_mode):
    """Start a task timer."""
    res = TaskResource(_make_session())
    _handle_api(res.start, id, json_mode=json_mode, entity="tasks")
    if not json_mode:
        print_success(f"Task {id} timer started.")


@tasks.command("stop")
@click.argument("id")
@_json_option
def tasks_stop(id, json_mode):
    """Stop a task timer."""
    res = TaskResource(_make_session())
    _handle_api(res.stop, id, json_mode=json_mode, entity="tasks")
    if not json_mode:
        print_success(f"Task {id} timer stopped.")


# ---------------------------------------------------------------------------
# projects
# ---------------------------------------------------------------------------

@cli.group()
def projects():
    """Manage projects."""


@projects.command("list")
@_json_option
@_page_option
@_per_page_option
@_filter_option
@click.option("--client-id", default=None)
@_all_option
def projects_list(json_mode, page, per_page, filter_text, client_id, all_pages):
    """List projects."""
    res = ProjectResource(_make_session())
    _handle_api(res.list, page=page, per_page=per_page, filter=filter_text,
                client_id=client_id, json_mode=json_mode, entity="projects", all_pages=all_pages)


@projects.command("get")
@click.argument("id")
@_json_option
def projects_get(id, json_mode):
    """Get a project by ID."""
    res = ProjectResource(_make_session())
    _handle_api(res.get, id, json_mode=json_mode, entity="projects")


@projects.command("create")
@click.option("--name", required=True, help="Project name.")
@click.option("--client-id", default=None, help="Client ID.")
@click.option("--due-date", default=None, help="Due date (YYYY-MM-DD).")
@click.option("--budgeted-hours", type=float, default=None)
@click.option("--task-rate", type=float, default=None)
@_json_option
def projects_create(name, client_id, due_date, budgeted_hours, task_rate, json_mode):
    """Create a new project."""
    data: dict = {"name": name}
    if client_id:
        data["client_id"] = client_id
    if due_date:
        data["due_date"] = due_date
    if budgeted_hours is not None:
        data["budgeted_hours"] = budgeted_hours
    if task_rate is not None:
        data["task_rate"] = task_rate
    res = ProjectResource(_make_session())
    _handle_api(res.create, data, json_mode=json_mode, entity="projects")


@projects.command("update")
@click.argument("id")
@click.option("--name", default=None)
@click.option("--client-id", default=None)
@click.option("--due-date", default=None)
@click.option("--budgeted-hours", type=float, default=None)
@click.option("--task-rate", type=float, default=None)
@_json_option
def projects_update(id, name, client_id, due_date, budgeted_hours, task_rate, json_mode):
    """Update a project by ID."""
    data: dict = {}
    if name:
        data["name"] = name
    if client_id:
        data["client_id"] = client_id
    if due_date:
        data["due_date"] = due_date
    if budgeted_hours is not None:
        data["budgeted_hours"] = budgeted_hours
    if task_rate is not None:
        data["task_rate"] = task_rate
    if not data:
        print_error("No fields to update.")
        sys.exit(1)
    res = ProjectResource(_make_session())
    _handle_api(res.update, id, data, json_mode=json_mode, entity="projects")


@projects.command("delete")
@click.argument("id")
def projects_delete(id):
    """Delete a project by ID."""
    if not click.confirm(f"Delete project {id}?"):
        return
    res = ProjectResource(_make_session())
    _handle_api(res.delete, id, entity="projects")


@projects.command("archive")
@click.argument("ids", nargs=-1, required=True)
@_json_option
def projects_archive(ids, json_mode):
    """Archive one or more projects."""
    res = ProjectResource(_make_session())
    _handle_api(res.archive, list(ids), json_mode=json_mode, entity="projects")


@projects.command("restore")
@click.argument("ids", nargs=-1, required=True)
@_json_option
def projects_restore(ids, json_mode):
    """Restore one or more archived projects."""
    res = ProjectResource(_make_session())
    _handle_api(res.restore, list(ids), json_mode=json_mode, entity="projects")


# ---------------------------------------------------------------------------
# vendors
# ---------------------------------------------------------------------------

@cli.group()
def vendors():
    """Manage vendors."""


@vendors.command("list")
@_json_option
@_page_option
@_per_page_option
@_filter_option
@_all_option
def vendors_list(json_mode, page, per_page, filter_text, all_pages):
    """List vendors."""
    res = VendorResource(_make_session())
    _handle_api(res.list, page=page, per_page=per_page, filter=filter_text,
                json_mode=json_mode, entity="vendors", all_pages=all_pages)


@vendors.command("get")
@click.argument("id")
@_json_option
def vendors_get(id, json_mode):
    """Get a vendor by ID."""
    res = VendorResource(_make_session())
    _handle_api(res.get, id, json_mode=json_mode, entity="vendors")


@vendors.command("create")
@click.option("--name", required=True, help="Vendor name.")
@click.option("--email", default=None)
@click.option("--phone", default=None)
@click.option("--city", default=None)
@_json_option
def vendors_create(name, email, phone, city, json_mode):
    """Create a new vendor."""
    data: dict = {"name": name}
    if email or phone:
        contact: dict = {}
        if email:
            contact["email"] = email
        if phone:
            contact["phone"] = phone
        data["contacts"] = [contact]
    if city:
        data["city"] = city
    res = VendorResource(_make_session())
    _handle_api(res.create, data, json_mode=json_mode, entity="vendors")


@vendors.command("update")
@click.argument("id")
@click.option("--name", default=None)
@click.option("--phone", default=None)
@click.option("--city", default=None)
@_json_option
def vendors_update(id, name, phone, city, json_mode):
    """Update a vendor by ID."""
    data: dict = {}
    if name:
        data["name"] = name
    if phone:
        data["phone"] = phone
    if city:
        data["city"] = city
    if not data:
        print_error("No fields to update.")
        sys.exit(1)
    res = VendorResource(_make_session())
    _handle_api(res.update, id, data, json_mode=json_mode, entity="vendors")


@vendors.command("delete")
@click.argument("id")
def vendors_delete(id):
    """Delete a vendor by ID."""
    if not click.confirm(f"Delete vendor {id}?"):
        return
    res = VendorResource(_make_session())
    _handle_api(res.delete, id, entity="vendors")


@vendors.command("archive")
@click.argument("ids", nargs=-1, required=True)
@_json_option
def vendors_archive(ids, json_mode):
    """Archive one or more vendors."""
    res = VendorResource(_make_session())
    _handle_api(res.archive, list(ids), json_mode=json_mode, entity="vendors")


@vendors.command("restore")
@click.argument("ids", nargs=-1, required=True)
@_json_option
def vendors_restore(ids, json_mode):
    """Restore one or more archived vendors."""
    res = VendorResource(_make_session())
    _handle_api(res.restore, list(ids), json_mode=json_mode, entity="vendors")


# ---------------------------------------------------------------------------
# expenses
# ---------------------------------------------------------------------------

@cli.group()
def expenses():
    """Manage expenses."""


@expenses.command("list")
@_json_option
@_page_option
@_per_page_option
@_filter_option
@click.option("--client-id", default=None)
@click.option("--vendor-id", default=None)
@_all_option
def expenses_list(json_mode, page, per_page, filter_text, client_id, vendor_id, all_pages):
    """List expenses."""
    res = ExpenseResource(_make_session())
    _handle_api(res.list, page=page, per_page=per_page, filter=filter_text,
                client_id=client_id, vendor_id=vendor_id,
                json_mode=json_mode, entity="expenses", all_pages=all_pages)


@expenses.command("get")
@click.argument("id")
@_json_option
def expenses_get(id, json_mode):
    """Get an expense by ID."""
    res = ExpenseResource(_make_session())
    _handle_api(res.get, id, json_mode=json_mode, entity="expenses")


@expenses.command("create")
@click.option("--amount", required=True, type=float, help="Expense amount.")
@click.option("--vendor-id", default=None, help="Vendor ID.")
@click.option("--client-id", default=None, help="Client ID (for billable expenses).")
@click.option("--date", "expense_date", default=None, help="Expense date (YYYY-MM-DD).")
@click.option("--notes", default=None, help="Public notes.")
@_json_option
def expenses_create(amount, vendor_id, client_id, expense_date, notes, json_mode):
    """Record a new expense."""
    data: dict = {"amount": amount}
    if vendor_id:
        data["vendor_id"] = vendor_id
    if client_id:
        data["client_id"] = client_id
    if expense_date:
        data["date"] = expense_date
    if notes:
        data["public_notes"] = notes
    res = ExpenseResource(_make_session())
    _handle_api(res.create, data, json_mode=json_mode, entity="expenses")


@expenses.command("update")
@click.argument("id")
@click.option("--amount", type=float, default=None)
@click.option("--date", "expense_date", default=None)
@click.option("--notes", default=None)
@_json_option
def expenses_update(id, amount, expense_date, notes, json_mode):
    """Update an expense by ID."""
    data: dict = {}
    if amount is not None:
        data["amount"] = amount
    if expense_date:
        data["date"] = expense_date
    if notes:
        data["public_notes"] = notes
    if not data:
        print_error("No fields to update.")
        sys.exit(1)
    res = ExpenseResource(_make_session())
    _handle_api(res.update, id, data, json_mode=json_mode, entity="expenses")


@expenses.command("delete")
@click.argument("id")
def expenses_delete(id):
    """Delete an expense by ID."""
    if not click.confirm(f"Delete expense {id}?"):
        return
    res = ExpenseResource(_make_session())
    _handle_api(res.delete, id, entity="expenses")


@expenses.command("archive")
@click.argument("ids", nargs=-1, required=True)
@_json_option
def expenses_archive(ids, json_mode):
    """Archive one or more expenses."""
    res = ExpenseResource(_make_session())
    _handle_api(res.archive, list(ids), json_mode=json_mode, entity="expenses")


@expenses.command("restore")
@click.argument("ids", nargs=-1, required=True)
@_json_option
def expenses_restore(ids, json_mode):
    """Restore one or more archived expenses."""
    res = ExpenseResource(_make_session())
    _handle_api(res.restore, list(ids), json_mode=json_mode, entity="expenses")


# ---------------------------------------------------------------------------
# credits
# ---------------------------------------------------------------------------

@cli.group()
def credits():
    """Manage credits."""


@credits.command("list")
@_json_option
@_page_option
@_per_page_option
@_filter_option
@click.option("--client-id", default=None)
@_all_option
def credits_list(json_mode, page, per_page, filter_text, client_id, all_pages):
    """List credits."""
    res = CreditResource(_make_session())
    _handle_api(res.list, page=page, per_page=per_page, filter=filter_text,
                client_id=client_id, json_mode=json_mode, entity="credits", all_pages=all_pages)


@credits.command("get")
@click.argument("id")
@_json_option
def credits_get(id, json_mode):
    """Get a credit by ID."""
    res = CreditResource(_make_session())
    _handle_api(res.get, id, json_mode=json_mode, entity="credits")


@credits.command("create")
@click.option("--client-id", required=True)
@click.option("--amount", required=True, type=float)
@click.option("--date", "credit_date", default=None)
@click.option("--notes", default=None)
@_json_option
def credits_create(client_id, amount, credit_date, notes, json_mode):
    """Create a new credit."""
    data: dict = {"client_id": client_id}
    if amount is not None:
        data["line_items"] = [{"quantity": 1, "cost": amount, "product_key": "Credit"}]
    if credit_date:
        data["date"] = credit_date
    if notes:
        data["public_notes"] = notes
    res = CreditResource(_make_session())
    _handle_api(res.create, data, json_mode=json_mode, entity="credits")


@credits.command("archive")
@click.argument("ids", nargs=-1, required=True)
@_json_option
def credits_archive(ids, json_mode):
    """Archive one or more credits."""
    res = CreditResource(_make_session())
    _handle_api(res.archive, list(ids), json_mode=json_mode, entity="credits")


@credits.command("restore")
@click.argument("ids", nargs=-1, required=True)
@_json_option
def credits_restore(ids, json_mode):
    """Restore one or more archived credits."""
    res = CreditResource(_make_session())
    _handle_api(res.restore, list(ids), json_mode=json_mode, entity="credits")


# ---------------------------------------------------------------------------
# recurring-invoices
# ---------------------------------------------------------------------------

@cli.group("recurring-invoices")
def recurring_invoices():
    """Manage recurring invoices."""


@recurring_invoices.command("list")
@_json_option
@_page_option
@_per_page_option
@_filter_option
@click.option("--client-id", default=None)
@_all_option
def ri_list(json_mode, page, per_page, filter_text, client_id, all_pages):
    """List recurring invoices."""
    res = RecurringInvoiceResource(_make_session())
    _handle_api(res.list, page=page, per_page=per_page, filter=filter_text,
                client_id=client_id, json_mode=json_mode, entity="recurring_invoices", all_pages=all_pages)


@recurring_invoices.command("get")
@click.argument("id")
@_json_option
def ri_get(id, json_mode):
    """Get a recurring invoice by ID."""
    res = RecurringInvoiceResource(_make_session())
    _handle_api(res.get, id, json_mode=json_mode, entity="recurring_invoices")


@recurring_invoices.command("start")
@click.argument("id")
@_json_option
def ri_start(id, json_mode):
    """Start a recurring invoice."""
    res = RecurringInvoiceResource(_make_session())
    _handle_api(res.start, id, json_mode=json_mode, entity="recurring_invoices")
    if not json_mode:
        print_success(f"Recurring invoice {id} started.")


@recurring_invoices.command("stop")
@click.argument("id")
@_json_option
def ri_stop(id, json_mode):
    """Stop a recurring invoice."""
    res = RecurringInvoiceResource(_make_session())
    _handle_api(res.stop, id, json_mode=json_mode, entity="recurring_invoices")
    if not json_mode:
        print_success(f"Recurring invoice {id} stopped.")


@recurring_invoices.command("archive")
@click.argument("ids", nargs=-1, required=True)
@_json_option
def ri_archive(ids, json_mode):
    """Archive one or more recurring invoices."""
    res = RecurringInvoiceResource(_make_session())
    _handle_api(res.archive, list(ids), json_mode=json_mode, entity="recurring_invoices")


@recurring_invoices.command("restore")
@click.argument("ids", nargs=-1, required=True)
@_json_option
def ri_restore(ids, json_mode):
    """Restore one or more archived recurring invoices."""
    res = RecurringInvoiceResource(_make_session())
    _handle_api(res.restore, list(ids), json_mode=json_mode, entity="recurring_invoices")


# ---------------------------------------------------------------------------
# purchase-orders
# ---------------------------------------------------------------------------

@cli.group("purchase-orders")
def purchase_orders():
    """Manage purchase orders."""


@purchase_orders.command("list")
@_json_option
@_page_option
@_per_page_option
@_filter_option
@click.option("--vendor-id", default=None)
@_all_option
def po_list(json_mode, page, per_page, filter_text, vendor_id, all_pages):
    """List purchase orders."""
    res = PurchaseOrderResource(_make_session())
    _handle_api(res.list, page=page, per_page=per_page, filter=filter_text,
                vendor_id=vendor_id, json_mode=json_mode, entity="purchase_orders", all_pages=all_pages)


@purchase_orders.command("get")
@click.argument("id")
@_json_option
def po_get(id, json_mode):
    """Get a purchase order by ID."""
    res = PurchaseOrderResource(_make_session())
    _handle_api(res.get, id, json_mode=json_mode, entity="purchase_orders")


@purchase_orders.command("send")
@click.argument("id")
@_json_option
def po_send(id, json_mode):
    """Email a purchase order to the vendor."""
    res = PurchaseOrderResource(_make_session())
    _handle_api(res.send, id, json_mode=json_mode, entity="purchase_orders")
    if not json_mode:
        print_success(f"Purchase order {id} emailed.")


@purchase_orders.command("archive")
@click.argument("ids", nargs=-1, required=True)
@_json_option
def po_archive(ids, json_mode):
    """Archive one or more purchase orders."""
    res = PurchaseOrderResource(_make_session())
    _handle_api(res.archive, list(ids), json_mode=json_mode, entity="purchase_orders")


@purchase_orders.command("restore")
@click.argument("ids", nargs=-1, required=True)
@_json_option
def po_restore(ids, json_mode):
    """Restore one or more archived purchase orders."""
    res = PurchaseOrderResource(_make_session())
    _handle_api(res.restore, list(ids), json_mode=json_mode, entity="purchase_orders")


# ---------------------------------------------------------------------------
# REPL
# ---------------------------------------------------------------------------

@cli.command()
def repl():
    """Launch an interactive REPL shell."""
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import InMemoryHistory
        from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
        _HAS_PROMPT_TOOLKIT = True
    except ImportError:
        _HAS_PROMPT_TOOLKIT = False

    import shlex

    click.echo("InvoiceNinja REPL — type 'help' for commands, 'exit' to quit.")

    if _HAS_PROMPT_TOOLKIT:
        session = PromptSession(
            history=InMemoryHistory(),
            auto_suggest=AutoSuggestFromHistory(),
        )
        get_input = lambda: session.prompt("invoiceninja> ")
    else:
        import readline  # noqa: F401 - enables readline editing
        get_input = lambda: input("invoiceninja> ")

    while True:
        try:
            line = get_input()
        except (EOFError, KeyboardInterrupt):
            click.echo("\nBye.")
            break

        line = line.strip()
        if not line:
            continue
        if line in ("exit", "quit", "q"):
            click.echo("Bye.")
            break
        if line == "help":
            ctx = click.Context(cli)
            click.echo(cli.get_help(ctx))
            continue

        try:
            args = shlex.split(line)
        except ValueError as exc:
            print_error(f"Parse error: {exc}")
            continue

        try:
            # Invoke the CLI programmatically; standalone_mode=False avoids sys.exit
            cli.main(args=args, standalone_mode=False)
        except SystemExit:
            pass
        except Exception as exc:
            print_error(str(exc))


# ---------------------------------------------------------------------------
# Module entry point (python -m invoiceninja_cli.invoiceninja_cli)
# ---------------------------------------------------------------------------

def main():
    cli()


if __name__ == "__main__":
    main()
