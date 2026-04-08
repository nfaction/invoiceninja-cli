"""End-to-end tests for invoiceninja-cli.

These tests hit a real InvoiceNinja API instance.
They are skipped unless INVOICENINJA_URL and INVOICENINJA_TOKEN are set.

Usage:
    export INVOICENINJA_URL=https://invoiceninja.example.com
    export INVOICENINJA_TOKEN=your_token
    pytest tests/test_full_e2e.py -v
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import unittest
from pathlib import Path

# Make sure the package is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

_URL = os.environ.get("INVOICENINJA_URL")
_TOKEN = os.environ.get("INVOICENINJA_TOKEN")
_SKIP = not (_URL and _TOKEN)
_SKIP_REASON = "INVOICENINJA_URL and INVOICENINJA_TOKEN must be set for E2E tests"


def _resolve_cli(name: str = "invoiceninja-cli") -> list[str]:
    """Resolve the CLI binary or fall back to python -m invocation.

    If CLI_ANYTHING_FORCE_INSTALLED=1 is set, uses shutil.which() to locate
    the installed binary. Otherwise falls back to python -m invocation so the
    tests work from source without installing.
    """
    if os.environ.get("CLI_ANYTHING_FORCE_INSTALLED"):
        path = shutil.which(name)
        if not path:
            raise RuntimeError(f"{name} not found in PATH")
        return [path]
    return [sys.executable, "-m", "invoiceninja_cli.invoiceninja_cli"]


def _run_cli(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run the CLI as a subprocess and return the CompletedProcess."""
    cmd = _resolve_cli() + list(args)
    merged_env = {**os.environ}
    if env:
        merged_env.update(env)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=merged_env,
        timeout=30,
    )


# ---------------------------------------------------------------------------
# Live connection test
# ---------------------------------------------------------------------------

@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestLiveConnection(unittest.TestCase):

    def test_ping(self):
        """Verify the API is reachable with the provided credentials."""
        from invoiceninja_cli.core.session import InvoiceNinjaSession, InvoiceNinjaAPIError
        session = InvoiceNinjaSession(_URL, _TOKEN)
        try:
            result = session.ping()
            self.assertIsInstance(result, dict)
        except InvoiceNinjaAPIError as exc:
            self.fail(f"Ping failed: {exc}")


# ---------------------------------------------------------------------------
# Live client lifecycle test
# ---------------------------------------------------------------------------

@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestLiveClients(unittest.TestCase):

    def setUp(self):
        from invoiceninja_cli.core.session import InvoiceNinjaSession
        from invoiceninja_cli.core.clients import ClientResource
        self.session = InvoiceNinjaSession(_URL, _TOKEN)
        self.resource = ClientResource(self.session)
        self._created_ids: list[str] = []

    def tearDown(self):
        """Clean up any clients created during tests."""
        for cid in self._created_ids:
            try:
                self.resource.delete(cid)
            except Exception:
                pass

    def _get_id(self, response: dict) -> str:
        data = response.get("data", {})
        return data.get("id", "")

    def test_create_list_get_delete_client(self):
        # Create
        unique_name = f"E2E Test Client {int(time.time())}"
        response = self.resource.create({"name": unique_name,
                                          "contacts": [{"email": "e2e@test.invalid"}]})
        self.assertIn("data", response)
        client_id = self._get_id(response)
        self.assertTrue(client_id, "Expected a client ID in create response")
        self._created_ids.append(client_id)

        # List — verify it appears
        list_resp = self.resource.list(per_page=100)
        records = list_resp.get("data", [])
        names = [r.get("name") for r in records]
        self.assertIn(unique_name, names)

        # Get single
        get_resp = self.resource.get(client_id)
        self.assertIn("data", get_resp)
        self.assertEqual(get_resp["data"].get("name"), unique_name)

        # Update
        updated_name = f"{unique_name} Updated"
        update_resp = self.resource.update(client_id, {"name": updated_name})
        self.assertEqual(update_resp["data"].get("name"), updated_name)

        # Archive + restore
        arc_resp = self.resource.archive([client_id])
        self.assertIsInstance(arc_resp, dict)
        rst_resp = self.resource.restore([client_id])
        self.assertIsInstance(rst_resp, dict)

        # Delete
        del_resp = self.resource.delete(client_id)
        self.assertIsInstance(del_resp, dict)
        self._created_ids.remove(client_id)


# ---------------------------------------------------------------------------
# Live invoice test
# ---------------------------------------------------------------------------

@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestLiveInvoices(unittest.TestCase):

    def setUp(self):
        from invoiceninja_cli.core.session import InvoiceNinjaSession
        from invoiceninja_cli.core.clients import ClientResource
        from invoiceninja_cli.core.invoices import InvoiceResource
        self.session = InvoiceNinjaSession(_URL, _TOKEN)
        self.clients = ClientResource(self.session)
        self.invoices = InvoiceResource(self.session)
        self._client_ids: list[str] = []
        self._invoice_ids: list[str] = []

        # Create a temporary client for invoice tests
        resp = self.clients.create({"name": f"E2E Invoice Client {int(time.time())}"})
        self._client_id = resp["data"]["id"]
        self._client_ids.append(self._client_id)

    def tearDown(self):
        for iid in self._invoice_ids:
            try:
                self.invoices.delete(iid)
            except Exception:
                pass
        for cid in self._client_ids:
            try:
                self.clients.delete(cid)
            except Exception:
                pass

    def test_create_and_list_invoice(self):
        resp = self.invoices.create({
            "client_id": self._client_id,
            "line_items": [{"quantity": 1, "cost": 250.0, "product_key": "E2E-TEST"}],
        })
        self.assertIn("data", resp)
        invoice_id = resp["data"]["id"]
        self.assertTrue(invoice_id)
        self._invoice_ids.append(invoice_id)

        # Verify it appears in the list
        list_resp = self.invoices.list(client_id=self._client_id, per_page=50)
        ids = [r.get("id") for r in list_resp.get("data", [])]
        self.assertIn(invoice_id, ids)

    def test_list_with_status_filter(self):
        resp = self.invoices.list(client_status="unpaid", per_page=5)
        self.assertIsInstance(resp, dict)


# ---------------------------------------------------------------------------
# Live product test
# ---------------------------------------------------------------------------

@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestLiveProducts(unittest.TestCase):

    def setUp(self):
        from invoiceninja_cli.core.session import InvoiceNinjaSession
        from invoiceninja_cli.core.products import ProductResource
        self.session = InvoiceNinjaSession(_URL, _TOKEN)
        self.resource = ProductResource(self.session)
        self._created_ids: list[str] = []

    def tearDown(self):
        for pid in self._created_ids:
            try:
                self.resource.delete(pid)
            except Exception:
                pass

    def test_create_and_delete_product(self):
        key = f"E2E-SKU-{int(time.time())}"
        resp = self.resource.create({
            "product_key": key,
            "price": 42.0,
            "notes": "E2E test product",
        })
        self.assertIn("data", resp)
        pid = resp["data"]["id"]
        self._created_ids.append(pid)

        get_resp = self.resource.get(pid)
        self.assertEqual(get_resp["data"]["product_key"], key)

        self.resource.delete(pid)
        self._created_ids.remove(pid)


# ---------------------------------------------------------------------------
# Live payment test
# ---------------------------------------------------------------------------

@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestLivePayments(unittest.TestCase):

    def setUp(self):
        from invoiceninja_cli.core.session import InvoiceNinjaSession
        from invoiceninja_cli.core.clients import ClientResource
        from invoiceninja_cli.core.payments import PaymentResource
        self.session = InvoiceNinjaSession(_URL, _TOKEN)
        self.clients = ClientResource(self.session)
        self.payments = PaymentResource(self.session)
        self._client_ids: list[str] = []
        self._payment_ids: list[str] = []

        resp = self.clients.create({"name": f"E2E Payment Client {int(time.time())}"})
        self._client_id = resp["data"]["id"]
        self._client_ids.append(self._client_id)

    def tearDown(self):
        for pid in self._payment_ids:
            try:
                self.payments.delete(pid)
            except Exception:
                pass
        for cid in self._client_ids:
            try:
                self.clients.delete(cid)
            except Exception:
                pass

    def test_create_payment(self):
        """Create a standalone payment (without an invoice)."""
        resp = self.payments.create({
            "client_id": self._client_id,
            "amount": 100.0,
            "type_id": "1",
        })
        self.assertIn("data", resp)
        payment_id = resp["data"].get("id")
        if payment_id:
            self._payment_ids.append(payment_id)
        self.assertTrue(payment_id)


# ---------------------------------------------------------------------------
# CLI Subprocess Tests
# ---------------------------------------------------------------------------

@unittest.skipIf(_SKIP, _SKIP_REASON)
class TestCLISubprocess(unittest.TestCase):
    """Run the CLI binary/module in a subprocess against the live API."""

    def test_ping_command(self):
        result = _run_cli("ping")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("successful", result.stdout.lower())

    def test_clients_list_json(self):
        result = _run_cli("clients", "list", "--json", "--per-page", "5")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        parsed = json.loads(result.stdout)
        self.assertIsInstance(parsed, dict)

    def test_clients_list_table(self):
        result = _run_cli("clients", "list", "--per-page", "5")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        # Table output is not empty (at minimum headers)
        self.assertGreater(len(result.stdout.strip()), 0)

    def test_invoices_list_json(self):
        result = _run_cli("invoices", "list", "--json", "--per-page", "5")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        parsed = json.loads(result.stdout)
        self.assertIsInstance(parsed, dict)

    def test_invoices_list_status_filter(self):
        result = _run_cli("invoices", "list", "--status", "unpaid", "--per-page", "5")
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_products_list_json(self):
        result = _run_cli("products", "list", "--json", "--per-page", "5")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        parsed = json.loads(result.stdout)
        self.assertIsInstance(parsed, dict)

    def test_invalid_command_exits_nonzero(self):
        result = _run_cli("nonexistent-command")
        self.assertNotEqual(result.returncode, 0)

    def test_version_flag(self):
        result = _run_cli("--version")
        self.assertEqual(result.returncode, 0)
        self.assertIn("0.1.0", result.stdout)

    def test_clients_create_and_delete(self):
        """Create a client via CLI, verify it, then delete it."""
        unique_name = f"E2E CLI Client {int(time.time())}"
        create_result = _run_cli(
            "clients", "create",
            "--name", unique_name,
            "--email", "clitest@e2e.invalid",
            "--json",
        )
        self.assertEqual(create_result.returncode, 0, msg=create_result.stderr)
        parsed = json.loads(create_result.stdout)
        client_id = parsed.get("data", {}).get("id")
        self.assertTrue(client_id, "Expected client ID in create response")

        try:
            # Verify by fetching
            get_result = _run_cli("clients", "get", client_id, "--json")
            self.assertEqual(get_result.returncode, 0, msg=get_result.stderr)
            get_parsed = json.loads(get_result.stdout)
            self.assertEqual(get_parsed.get("data", {}).get("name"), unique_name)
        finally:
            # Clean up — confirm deletion (bypass the prompt)
            from invoiceninja_cli.core.session import InvoiceNinjaSession
            from invoiceninja_cli.core.clients import ClientResource
            sess = InvoiceNinjaSession(_URL, _TOKEN)
            ClientResource(sess).delete(client_id)


if __name__ == "__main__":
    unittest.main()
