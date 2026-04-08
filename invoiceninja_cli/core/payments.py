"""Payment resource operations for InvoiceNinja."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .session import InvoiceNinjaSession

_ENTITY = "payments"


class PaymentResource:
    """CRUD + bulk operations on InvoiceNinja payments."""

    def __init__(self, session: InvoiceNinjaSession):
        self.session = session

    def list(
        self,
        page: int = 1,
        per_page: int = 20,
        filter: Optional[str] = None,
        client_id: Optional[str] = None,
        all_pages: bool = False,
        **kwargs: Any) -> dict:
        """List payments with optional filters."""
        params: Dict[str, Any] = {"page": page, "per_page": per_page, "include": "client"}
        if filter:
            params["filter"] = filter
        if client_id:
            params["client_id"] = client_id
        params.update(kwargs)
        if all_pages:
            return self.session.get_all_pages(_ENTITY, params)
        return self.session.get(_ENTITY, params=params)

    def get(self, id: str) -> dict:
        """Fetch a single payment by ID."""
        return self.session.get(f"{_ENTITY}/{id}")

    def create(self, data: Dict[str, Any]) -> dict:
        """Create a new payment.

        Expected data keys:
            client_id (str): Client ID.
            invoices (list): List of dicts with invoice_id and amount.
            date (str): Payment date YYYY-MM-DD.
            type_id (str): Payment type ID.
            amount (float): Total amount paid.
        """
        return self.session.post(_ENTITY, data=data)

    def update(self, id: str, data: Dict[str, Any]) -> dict:
        """Update an existing payment."""
        return self.session.put(f"{_ENTITY}/{id}", data=data)

    def delete(self, id: str) -> dict:
        """Delete a payment by ID."""
        return self.session.delete(f"{_ENTITY}/{id}")

    def archive(self, ids: List[str]) -> dict:
        """Archive one or more payments."""
        return self.session.bulk(_ENTITY, "archive", ids)

    def restore(self, ids: List[str]) -> dict:
        """Restore one or more archived payments."""
        return self.session.bulk(_ENTITY, "restore", ids)
