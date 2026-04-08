"""Quote resource operations for InvoiceNinja."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .session import InvoiceNinjaSession

_ENTITY = "quotes"


class QuoteResource:
    """CRUD + bulk + action operations on InvoiceNinja quotes."""

    def __init__(self, session: InvoiceNinjaSession):
        self.session = session

    def list(
        self,
        page: int = 1,
        per_page: int = 20,
        filter: Optional[str] = None,
        client_id: Optional[str] = None,
        client_status: Optional[str] = None,
        all_pages: bool = False,
        **kwargs: Any) -> dict:
        """List quotes with optional filters."""
        params: Dict[str, Any] = {"page": page, "per_page": per_page, "include": "client"}
        if filter:
            params["filter"] = filter
        if client_id:
            params["client_id"] = client_id
        if client_status:
            params["client_status"] = client_status
        params.update(kwargs)
        if all_pages:
            return self.session.get_all_pages(_ENTITY, params)
        return self.session.get(_ENTITY, params=params)

    def get(self, id: str) -> dict:
        """Fetch a single quote by ID."""
        return self.session.get(f"{_ENTITY}/{id}")

    def create(self, data: Dict[str, Any]) -> dict:
        """Create a new quote."""
        return self.session.post(_ENTITY, data=data)

    def update(self, id: str, data: Dict[str, Any]) -> dict:
        """Update an existing quote."""
        return self.session.put(f"{_ENTITY}/{id}", data=data)

    def delete(self, id: str) -> dict:
        """Delete a quote by ID."""
        return self.session.delete(f"{_ENTITY}/{id}")

    def archive(self, ids: List[str]) -> dict:
        """Archive one or more quotes."""
        return self.session.bulk(_ENTITY, "archive", ids)

    def restore(self, ids: List[str]) -> dict:
        """Restore one or more archived quotes."""
        return self.session.bulk(_ENTITY, "restore", ids)

    def approve(self, id: str) -> dict:
        """Approve a quote."""
        return self.session.bulk(_ENTITY, "approve", [id])

    def send(self, id: str) -> dict:
        """Email a quote to the client."""
        return self.session.bulk(_ENTITY, "email", [id])
