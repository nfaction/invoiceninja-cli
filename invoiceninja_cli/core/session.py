"""API session management for InvoiceNinja v5."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests
from requests import Response


class InvoiceNinjaAPIError(Exception):
    """Raised when the API returns an error response."""

    def __init__(self, status_code: int, message: str, raw: Any = None):
        self.status_code = status_code
        self.message = message
        self.raw = raw
        super().__init__(f"HTTP {status_code}: {message}")


class InvoiceNinjaSession:
    """Manages authenticated HTTP communication with the InvoiceNinja API."""

    def __init__(self, url: str, token: str, timeout: int = 30):
        self.base_url = url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-API-TOKEN": token,
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    def _url(self, path: str) -> str:
        path = path.lstrip("/")
        return f"{self.base_url}/api/v1/{path}"

    def _handle_response(self, response: Response) -> Any:
        """Raise InvoiceNinjaAPIError on non-2xx responses; return parsed JSON."""
        if response.status_code == 204:
            return {}
        try:
            payload = response.json()
        except ValueError:
            payload = response.text

        if not response.ok:
            # Try to extract a human-friendly message
            if isinstance(payload, dict):
                message = (
                    payload.get("message")
                    or payload.get("error")
                    or str(payload)
                )
            else:
                message = str(payload) or response.reason
            raise InvoiceNinjaAPIError(response.status_code, message, raw=payload)

        return payload

    def get(self, path: str, params: Optional[Dict] = None) -> Any:
        """Perform an authenticated GET request."""
        response = self.session.get(
            self._url(path), params=params, timeout=self.timeout
        )
        return self._handle_response(response)

    def post(self, path: str, data: Optional[Dict] = None) -> Any:
        """Perform an authenticated POST request."""
        import json

        response = self.session.post(
            self._url(path),
            data=json.dumps(data or {}),
            timeout=self.timeout,
        )
        return self._handle_response(response)

    def put(self, path: str, data: Optional[Dict] = None) -> Any:
        """Perform an authenticated PUT request."""
        import json

        response = self.session.put(
            self._url(path),
            data=json.dumps(data or {}),
            timeout=self.timeout,
        )
        return self._handle_response(response)

    def delete(self, path: str) -> Any:
        """Perform an authenticated DELETE request."""
        response = self.session.delete(self._url(path), timeout=self.timeout)
        return self._handle_response(response)

    def bulk(self, entity: str, action: str, ids: List[str]) -> Any:
        """POST /api/v1/{entity}/bulk with a given action and list of IDs."""
        return self.post(
            f"{entity}/bulk",
            data={"action": action, "ids": ids},
        )

    def get_all_pages(self, path: str, params: Optional[Dict] = None, page_size: int = 100) -> Dict:
        """Fetch every page of a paginated list endpoint and return a merged result.

        Returns a dict of the form ``{"data": [all records], "meta": {pagination of last page}}``
        so callers can treat it identically to a single-page response.
        """
        params = dict(params or {})
        params["per_page"] = page_size
        params["page"] = 1

        all_records: list = []
        last_meta: dict = {}

        while True:
            response = self.get(path, params=params)
            page_data = response.get("data", [])
            if isinstance(page_data, list):
                all_records.extend(page_data)
            elif isinstance(page_data, dict):
                # Single-record response — shouldn't happen on list endpoints
                all_records.append(page_data)

            last_meta = response.get("meta", {})
            pagination = last_meta.get("pagination", {})
            current = pagination.get("current_page", 1)
            total_pages = pagination.get("total_pages", 1)

            if current >= total_pages:
                break
            params["page"] = current + 1

        return {"data": all_records, "meta": last_meta}

    def ping(self) -> dict:
        """Quick connectivity check — fetch the company settings endpoint."""
        return self.get("company_users")
