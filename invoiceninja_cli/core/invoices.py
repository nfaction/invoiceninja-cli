"""Invoice resource operations for InvoiceNinja."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .session import InvoiceNinjaSession

_ENTITY = "invoices"


class InvoiceResource:
    """CRUD + bulk + action operations on InvoiceNinja invoices."""

    def __init__(self, session: InvoiceNinjaSession):
        self.session = session

    def list(
        self,
        page: int = 1,
        per_page: int = 20,
        filter: Optional[str] = None,
        client_status: Optional[str] = None,
        client_id: Optional[str] = None,
        number: Optional[str] = None,
        all_pages: bool = False,
        **kwargs: Any) -> dict:
        """List invoices with optional filters.

        Args:
            client_status: paid | unpaid | overdue
            client_id: Filter by client ID.
            number: Filter by invoice number.
            filter: Full-text filter string.
        """
        params: Dict[str, Any] = {"page": page, "per_page": per_page, "include": "client"}
        if filter:
            params["filter"] = filter
        if client_status:
            params["client_status"] = client_status
        if client_id:
            params["client_id"] = client_id
        if number:
            params["number"] = number
        params.update(kwargs)
        if all_pages:
            return self.session.get_all_pages(_ENTITY, params)
        return self.session.get(_ENTITY, params=params)

    def get(self, id: str) -> dict:
        """Fetch a single invoice by ID."""
        return self.session.get(f"{_ENTITY}/{id}")

    def create(self, data: Dict[str, Any]) -> dict:
        """Create a new invoice."""
        return self.session.post(_ENTITY, data=data)

    def update(self, id: str, data: Dict[str, Any]) -> dict:
        """Update an existing invoice."""
        return self.session.put(f"{_ENTITY}/{id}", data=data)

    def delete(self, id: str) -> dict:
        """Delete an invoice by ID."""
        return self.session.delete(f"{_ENTITY}/{id}")

    def archive(self, ids: List[str]) -> dict:
        """Archive one or more invoices."""
        return self.session.bulk(_ENTITY, "archive", ids)

    def restore(self, ids: List[str]) -> dict:
        """Restore one or more archived invoices."""
        return self.session.bulk(_ENTITY, "restore", ids)

    def send(self, id: str) -> dict:
        """Email an invoice to the client."""
        return self.session.bulk(_ENTITY, "email", [id])

    def mark_paid(self, id: str) -> dict:
        """Mark an invoice as paid."""
        return self.session.bulk(_ENTITY, "mark_paid", [id])

    def mark_sent(self, id: str) -> dict:
        """Mark an invoice as sent (without emailing)."""
        return self.session.bulk(_ENTITY, "mark_sent", [id])
