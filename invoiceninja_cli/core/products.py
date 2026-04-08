"""Product resource operations for InvoiceNinja."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .session import InvoiceNinjaSession

_ENTITY = "products"


class ProductResource:
    """CRUD + bulk operations on InvoiceNinja products."""

    def __init__(self, session: InvoiceNinjaSession):
        self.session = session

    def list(
        self,
        page: int = 1,
        per_page: int = 20,
        filter: Optional[str] = None,
        all_pages: bool = False,
        **kwargs: Any) -> dict:
        """List products."""
        params: Dict[str, Any] = {"page": page, "per_page": per_page}
        if filter:
            params["filter"] = filter
        params.update(kwargs)
        if all_pages:
            return self.session.get_all_pages(_ENTITY, params)
        return self.session.get(_ENTITY, params=params)

    def get(self, id: str) -> dict:
        """Fetch a single product by ID."""
        return self.session.get(f"{_ENTITY}/{id}")

    def create(self, data: Dict[str, Any]) -> dict:
        """Create a new product.

        Expected data keys:
            product_key (str): SKU / product key.
            notes (str): Description.
            price (float): Unit price.
            quantity (float): Default quantity.
        """
        return self.session.post(_ENTITY, data=data)

    def update(self, id: str, data: Dict[str, Any]) -> dict:
        """Update an existing product."""
        return self.session.put(f"{_ENTITY}/{id}", data=data)

    def delete(self, id: str) -> dict:
        """Delete a product by ID."""
        return self.session.delete(f"{_ENTITY}/{id}")

    def archive(self, ids: List[str]) -> dict:
        """Archive one or more products."""
        return self.session.bulk(_ENTITY, "archive", ids)

    def restore(self, ids: List[str]) -> dict:
        """Restore one or more archived products."""
        return self.session.bulk(_ENTITY, "restore", ids)
