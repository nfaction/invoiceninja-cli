"""Unit tests for invoiceninja-cli core modules.

No network access — all HTTP calls are mocked with unittest.mock.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch, call

# ---------------------------------------------------------------------------
# Ensure the package is importable when running from the tests/ directory
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from invoiceninja_cli.core.session import InvoiceNinjaSession, InvoiceNinjaAPIError
from invoiceninja_cli.core.clients import ClientResource
from invoiceninja_cli.core.invoices import InvoiceResource
from invoiceninja_cli.core.quotes import QuoteResource
from invoiceninja_cli.core.payments import PaymentResource
from invoiceninja_cli.core.products import ProductResource
from invoiceninja_cli.core.projects import ProjectResource
from invoiceninja_cli.core.tasks import TaskResource
from invoiceninja_cli.core.vendors import VendorResource
from invoiceninja_cli.core.expenses import ExpenseResource
from invoiceninja_cli.core.credits import CreditResource
from invoiceninja_cli.core.recurring_invoices import RecurringInvoiceResource
from invoiceninja_cli.core.purchase_orders import PurchaseOrderResource
from invoiceninja_cli.utils import config as config_module
from invoiceninja_cli.utils.output import format_output


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(status_code: int, payload: dict | str):
    """Create a mock requests.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = (200 <= status_code < 300)
    resp.reason = "OK" if resp.ok else "Error"
    if isinstance(payload, dict):
        resp.json.return_value = payload
    else:
        resp.json.side_effect = ValueError("not json")
        resp.text = payload
    return resp


def _session() -> InvoiceNinjaSession:
    return InvoiceNinjaSession("https://ninja.example.com", "test-token-abc")


# ---------------------------------------------------------------------------
# Session Tests
# ---------------------------------------------------------------------------

class TestInvoiceNinjaSession(unittest.TestCase):

    def setUp(self):
        self.session = _session()

    def test_base_url_strips_trailing_slash(self):
        s = InvoiceNinjaSession("https://ninja.example.com/", "tok")
        self.assertEqual(s.base_url, "https://ninja.example.com")

    def test_get_calls_correct_url(self):
        with patch.object(self.session.session, "get") as mock_get:
            mock_get.return_value = _make_response(200, {"data": []})
            self.session.get("clients")
            mock_get.assert_called_once_with(
                "https://ninja.example.com/api/v1/clients",
                params=None,
                timeout=30,
            )

    def test_get_with_params(self):
        with patch.object(self.session.session, "get") as mock_get:
            mock_get.return_value = _make_response(200, {"data": []})
            self.session.get("clients", params={"page": 2})
            mock_get.assert_called_once_with(
                "https://ninja.example.com/api/v1/clients",
                params={"page": 2},
                timeout=30,
            )

    def test_post_sends_json_body(self):
        with patch.object(self.session.session, "post") as mock_post:
            mock_post.return_value = _make_response(200, {"data": {}})
            self.session.post("clients", data={"name": "Acme"})
            mock_post.assert_called_once_with(
                "https://ninja.example.com/api/v1/clients",
                data=json.dumps({"name": "Acme"}),
                timeout=30,
            )

    def test_put_sends_json_body(self):
        with patch.object(self.session.session, "put") as mock_put:
            mock_put.return_value = _make_response(200, {"data": {}})
            self.session.put("clients/1", data={"name": "New"})
            mock_put.assert_called_once_with(
                "https://ninja.example.com/api/v1/clients/1",
                data=json.dumps({"name": "New"}),
                timeout=30,
            )

    def test_delete_calls_delete(self):
        with patch.object(self.session.session, "delete") as mock_del:
            mock_del.return_value = _make_response(200, {"data": {}})
            self.session.delete("clients/1")
            mock_del.assert_called_once_with(
                "https://ninja.example.com/api/v1/clients/1",
                timeout=30,
            )

    def test_bulk_posts_correct_payload(self):
        with patch.object(self.session, "post") as mock_post:
            mock_post.return_value = {"data": []}
            self.session.bulk("clients", "archive", ["id1", "id2"])
            mock_post.assert_called_once_with(
                "clients/bulk",
                data={"action": "archive", "ids": ["id1", "id2"]},
            )

    def test_api_error_raised_on_401(self):
        with patch.object(self.session.session, "get") as mock_get:
            mock_get.return_value = _make_response(401, {"message": "Unauthenticated."})
            with self.assertRaises(InvoiceNinjaAPIError) as ctx:
                self.session.get("clients")
            self.assertEqual(ctx.exception.status_code, 401)

    def test_api_error_raised_on_404(self):
        with patch.object(self.session.session, "get") as mock_get:
            mock_get.return_value = _make_response(404, {"message": "Not Found"})
            with self.assertRaises(InvoiceNinjaAPIError):
                self.session.get("clients/nonexistent")

    def test_api_error_raised_on_500(self):
        with patch.object(self.session.session, "get") as mock_get:
            mock_get.return_value = _make_response(500, "Internal Server Error")
            with self.assertRaises(InvoiceNinjaAPIError) as ctx:
                self.session.get("clients")
            self.assertEqual(ctx.exception.status_code, 500)

    def test_204_returns_empty_dict(self):
        with patch.object(self.session.session, "delete") as mock_del:
            resp = MagicMock()
            resp.status_code = 204
            resp.ok = True
            mock_del.return_value = resp
            result = self.session.delete("clients/1")
            self.assertEqual(result, {})

    def test_request_headers(self):
        headers = dict(self.session.session.headers)
        self.assertEqual(headers["X-API-TOKEN"], "test-token-abc")
        self.assertEqual(headers["X-Requested-With"], "XMLHttpRequest")
        self.assertEqual(headers["Accept"], "application/json")


# ---------------------------------------------------------------------------
# Config Tests
# ---------------------------------------------------------------------------

class TestConfig(unittest.TestCase):

    def setUp(self):
        self._orig_config_file = config_module.CONFIG_FILE
        self._orig_config_dir = config_module.CONFIG_DIR
        self._tmpdir = tempfile.mkdtemp()
        config_module.CONFIG_DIR = Path(self._tmpdir)
        config_module.CONFIG_FILE = Path(self._tmpdir) / "config.json"

    def tearDown(self):
        config_module.CONFIG_FILE = self._orig_config_file
        config_module.CONFIG_DIR = self._orig_config_dir
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_load_config_missing_file_returns_empty(self):
        result = config_module.load_config()
        self.assertEqual(result, {})

    def test_save_and_load_roundtrip(self):
        data = {"url": "https://test.com", "token": "abc123"}
        config_module.save_config(data)
        loaded = config_module.load_config()
        self.assertEqual(loaded, data)

    def test_get_config_env_vars_override(self):
        config_module.save_config({"url": "https://file.com", "token": "file_token"})
        with patch.dict(os.environ, {"INVOICENINJA_URL": "https://env.com",
                                      "INVOICENINJA_TOKEN": "env_token"}):
            cfg = config_module.get_config()
        self.assertEqual(cfg["url"], "https://env.com")
        self.assertEqual(cfg["token"], "env_token")

    def test_get_config_returns_file_when_no_env(self):
        config_module.save_config({"url": "https://file.com", "token": "file_token"})
        env = {k: v for k, v in os.environ.items()
               if k not in ("INVOICENINJA_URL", "INVOICENINJA_TOKEN")}
        with patch.dict(os.environ, env, clear=True):
            cfg = config_module.get_config()
        self.assertEqual(cfg["url"], "https://file.com")

    def test_require_config_raises_when_missing_url(self):
        config_module.save_config({"token": "abc"})
        env = {k: v for k, v in os.environ.items()
               if k not in ("INVOICENINJA_URL", "INVOICENINJA_TOKEN")}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                config_module.require_config()
        self.assertIn("url", str(ctx.exception))

    def test_require_config_raises_when_missing_token(self):
        config_module.save_config({"url": "https://test.com"})
        env = {k: v for k, v in os.environ.items()
               if k not in ("INVOICENINJA_URL", "INVOICENINJA_TOKEN")}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                config_module.require_config()
        self.assertIn("token", str(ctx.exception))

    def test_require_config_returns_config_when_complete(self):
        config_module.save_config({"url": "https://test.com", "token": "abc"})
        env = {k: v for k, v in os.environ.items()
               if k not in ("INVOICENINJA_URL", "INVOICENINJA_TOKEN")}
        with patch.dict(os.environ, env, clear=True):
            cfg = config_module.require_config()
        self.assertEqual(cfg["url"], "https://test.com")


# ---------------------------------------------------------------------------
# Base class for resource tests
# ---------------------------------------------------------------------------

class ResourceTestBase(unittest.TestCase):
    """Shared setup for resource tests."""

    def setUp(self):
        self.session = _session()
        self._patch_get = patch.object(self.session, "get", return_value={"data": []})
        self._patch_post = patch.object(self.session, "post", return_value={"data": {}})
        self._patch_put = patch.object(self.session, "put", return_value={"data": {}})
        self._patch_delete = patch.object(self.session, "delete", return_value={})
        self._patch_bulk = patch.object(self.session, "bulk", return_value={"data": []})
        self.mock_get = self._patch_get.start()
        self.mock_post = self._patch_post.start()
        self.mock_put = self._patch_put.start()
        self.mock_delete = self._patch_delete.start()
        self.mock_bulk = self._patch_bulk.start()

    def tearDown(self):
        self._patch_get.stop()
        self._patch_post.stop()
        self._patch_put.stop()
        self._patch_delete.stop()
        self._patch_bulk.stop()


# ---------------------------------------------------------------------------
# ClientResource Tests
# ---------------------------------------------------------------------------

class TestClientResource(ResourceTestBase):

    def setUp(self):
        super().setUp()
        self.resource = ClientResource(self.session)

    def test_list_calls_get(self):
        self.resource.list()
        self.mock_get.assert_called_once_with("clients", params={"page": 1, "per_page": 20})

    def test_list_passes_filter(self):
        self.resource.list(filter="acme")
        args, kwargs = self.mock_get.call_args
        self.assertEqual(kwargs["params"]["filter"], "acme")

    def test_list_passes_status(self):
        self.resource.list(status="active")
        args, kwargs = self.mock_get.call_args
        self.assertEqual(kwargs["params"]["client_status"], "active")

    def test_get_calls_correct_path(self):
        self.resource.get("client-123")
        self.mock_get.assert_called_once_with("clients/client-123")

    def test_create_posts_data(self):
        self.resource.create({"name": "Acme"})
        self.mock_post.assert_called_once_with("clients", data={"name": "Acme"})

    def test_update_puts_data(self):
        self.resource.update("c-1", {"name": "New"})
        self.mock_put.assert_called_once_with("clients/c-1", data={"name": "New"})

    def test_delete_calls_delete(self):
        self.resource.delete("c-1")
        self.mock_delete.assert_called_once_with("clients/c-1")

    def test_archive_calls_bulk(self):
        self.resource.archive(["c-1", "c-2"])
        self.mock_bulk.assert_called_once_with("clients", "archive", ["c-1", "c-2"])

    def test_restore_calls_bulk(self):
        self.resource.restore(["c-1"])
        self.mock_bulk.assert_called_once_with("clients", "restore", ["c-1"])


# ---------------------------------------------------------------------------
# InvoiceResource Tests
# ---------------------------------------------------------------------------

class TestInvoiceResource(ResourceTestBase):

    def setUp(self):
        super().setUp()
        self.resource = InvoiceResource(self.session)

    def test_list_calls_get(self):
        self.resource.list()
        self.mock_get.assert_called_once()
        args, kwargs = self.mock_get.call_args
        self.assertEqual(args[0], "invoices")

    def test_list_filters_passed(self):
        self.resource.list(client_status="unpaid", client_id="c-1", number="INV-001")
        args, kwargs = self.mock_get.call_args
        params = kwargs["params"]
        self.assertEqual(params["client_status"], "unpaid")
        self.assertEqual(params["client_id"], "c-1")
        self.assertEqual(params["number"], "INV-001")

    def test_get_calls_correct_path(self):
        self.resource.get("inv-1")
        self.mock_get.assert_called_once_with("invoices/inv-1")

    def test_create_posts_data(self):
        data = {"client_id": "c-1", "line_items": []}
        self.resource.create(data)
        self.mock_post.assert_called_once_with("invoices", data=data)

    def test_update_puts_data(self):
        self.resource.update("inv-1", {"date": "2024-01-01"})
        self.mock_put.assert_called_once_with("invoices/inv-1", data={"date": "2024-01-01"})

    def test_delete_calls_delete(self):
        self.resource.delete("inv-1")
        self.mock_delete.assert_called_once_with("invoices/inv-1")

    def test_archive_calls_bulk(self):
        self.resource.archive(["inv-1"])
        self.mock_bulk.assert_called_once_with("invoices", "archive", ["inv-1"])

    def test_restore_calls_bulk(self):
        self.resource.restore(["inv-1"])
        self.mock_bulk.assert_called_once_with("invoices", "restore", ["inv-1"])

    def test_send_bulk_email(self):
        self.resource.send("inv-1")
        self.mock_bulk.assert_called_once_with("invoices", "email", ["inv-1"])

    def test_mark_paid_bulk(self):
        self.resource.mark_paid("inv-1")
        self.mock_bulk.assert_called_once_with("invoices", "mark_paid", ["inv-1"])

    def test_mark_sent_bulk(self):
        self.resource.mark_sent("inv-1")
        self.mock_bulk.assert_called_once_with("invoices", "mark_sent", ["inv-1"])


# ---------------------------------------------------------------------------
# QuoteResource Tests
# ---------------------------------------------------------------------------

class TestQuoteResource(ResourceTestBase):

    def setUp(self):
        super().setUp()
        self.resource = QuoteResource(self.session)

    def test_list_calls_get(self):
        self.resource.list()
        self.mock_get.assert_called_once()

    def test_get_calls_correct_path(self):
        self.resource.get("q-1")
        self.mock_get.assert_called_once_with("quotes/q-1")

    def test_create_posts_data(self):
        self.resource.create({"client_id": "c-1"})
        self.mock_post.assert_called_once_with("quotes", data={"client_id": "c-1"})

    def test_update_puts_data(self):
        self.resource.update("q-1", {"valid_until": "2024-12-31"})
        self.mock_put.assert_called_once_with("quotes/q-1", data={"valid_until": "2024-12-31"})

    def test_delete_calls_delete(self):
        self.resource.delete("q-1")
        self.mock_delete.assert_called_once_with("quotes/q-1")

    def test_archive_calls_bulk(self):
        self.resource.archive(["q-1", "q-2"])
        self.mock_bulk.assert_called_once_with("quotes", "archive", ["q-1", "q-2"])

    def test_restore_calls_bulk(self):
        self.resource.restore(["q-1"])
        self.mock_bulk.assert_called_once_with("quotes", "restore", ["q-1"])

    def test_approve_calls_bulk(self):
        self.resource.approve("q-1")
        self.mock_bulk.assert_called_once_with("quotes", "approve", ["q-1"])

    def test_send_calls_bulk_email(self):
        self.resource.send("q-1")
        self.mock_bulk.assert_called_once_with("quotes", "email", ["q-1"])


# ---------------------------------------------------------------------------
# PaymentResource Tests
# ---------------------------------------------------------------------------

class TestPaymentResource(ResourceTestBase):

    def setUp(self):
        super().setUp()
        self.resource = PaymentResource(self.session)

    def test_list_calls_get(self):
        self.resource.list()
        self.mock_get.assert_called_once()

    def test_list_with_client_id(self):
        self.resource.list(client_id="c-1")
        args, kwargs = self.mock_get.call_args
        self.assertEqual(kwargs["params"]["client_id"], "c-1")

    def test_get_calls_correct_path(self):
        self.resource.get("p-1")
        self.mock_get.assert_called_once_with("payments/p-1")

    def test_create_posts_data(self):
        data = {"client_id": "c-1", "amount": 100.0}
        self.resource.create(data)
        self.mock_post.assert_called_once_with("payments", data=data)

    def test_update_puts_data(self):
        self.resource.update("p-1", {"amount": 200.0})
        self.mock_put.assert_called_once_with("payments/p-1", data={"amount": 200.0})

    def test_delete_calls_delete(self):
        self.resource.delete("p-1")
        self.mock_delete.assert_called_once_with("payments/p-1")

    def test_archive_calls_bulk(self):
        self.resource.archive(["p-1"])
        self.mock_bulk.assert_called_once_with("payments", "archive", ["p-1"])

    def test_restore_calls_bulk(self):
        self.resource.restore(["p-1"])
        self.mock_bulk.assert_called_once_with("payments", "restore", ["p-1"])


# ---------------------------------------------------------------------------
# ProductResource Tests
# ---------------------------------------------------------------------------

class TestProductResource(ResourceTestBase):

    def setUp(self):
        super().setUp()
        self.resource = ProductResource(self.session)

    def test_list_calls_get(self):
        self.resource.list()
        self.mock_get.assert_called_once()

    def test_get_calls_correct_path(self):
        self.resource.get("prod-1")
        self.mock_get.assert_called_once_with("products/prod-1")

    def test_create_posts_data(self):
        data = {"product_key": "SKU-001", "price": 9.99}
        self.resource.create(data)
        self.mock_post.assert_called_once_with("products", data=data)

    def test_update_puts_data(self):
        self.resource.update("prod-1", {"price": 19.99})
        self.mock_put.assert_called_once_with("products/prod-1", data={"price": 19.99})

    def test_delete_calls_delete(self):
        self.resource.delete("prod-1")
        self.mock_delete.assert_called_once_with("products/prod-1")

    def test_archive_calls_bulk(self):
        self.resource.archive(["prod-1"])
        self.mock_bulk.assert_called_once_with("products", "archive", ["prod-1"])

    def test_restore_calls_bulk(self):
        self.resource.restore(["prod-1"])
        self.mock_bulk.assert_called_once_with("products", "restore", ["prod-1"])


# ---------------------------------------------------------------------------
# ProjectResource Tests
# ---------------------------------------------------------------------------

class TestProjectResource(ResourceTestBase):

    def setUp(self):
        super().setUp()
        self.resource = ProjectResource(self.session)

    def test_list_calls_get(self):
        self.resource.list()
        self.mock_get.assert_called_once()

    def test_list_with_client_id(self):
        self.resource.list(client_id="c-1")
        args, kwargs = self.mock_get.call_args
        self.assertEqual(kwargs["params"]["client_id"], "c-1")

    def test_get_calls_correct_path(self):
        self.resource.get("proj-1")
        self.mock_get.assert_called_once_with("projects/proj-1")

    def test_create_posts_data(self):
        self.resource.create({"name": "My Project", "client_id": "c-1"})
        self.mock_post.assert_called_once()

    def test_update_puts_data(self):
        self.resource.update("proj-1", {"name": "New Name"})
        self.mock_put.assert_called_once_with("projects/proj-1", data={"name": "New Name"})

    def test_delete_calls_delete(self):
        self.resource.delete("proj-1")
        self.mock_delete.assert_called_once_with("projects/proj-1")

    def test_archive_calls_bulk(self):
        self.resource.archive(["proj-1"])
        self.mock_bulk.assert_called_once_with("projects", "archive", ["proj-1"])

    def test_restore_calls_bulk(self):
        self.resource.restore(["proj-1"])
        self.mock_bulk.assert_called_once_with("projects", "restore", ["proj-1"])


# ---------------------------------------------------------------------------
# TaskResource Tests
# ---------------------------------------------------------------------------

class TestTaskResource(ResourceTestBase):

    def setUp(self):
        super().setUp()
        self.resource = TaskResource(self.session)

    def test_list_calls_get(self):
        self.resource.list()
        self.mock_get.assert_called_once()

    def test_list_with_client_id(self):
        self.resource.list(client_id="c-1")
        args, kwargs = self.mock_get.call_args
        self.assertEqual(kwargs["params"]["client_id"], "c-1")

    def test_list_with_project_id(self):
        self.resource.list(project_id="proj-1")
        args, kwargs = self.mock_get.call_args
        self.assertEqual(kwargs["params"]["project_id"], "proj-1")

    def test_get_calls_correct_path(self):
        self.resource.get("task-1")
        self.mock_get.assert_called_once_with("tasks/task-1")

    def test_create_posts_data(self):
        self.resource.create({"description": "Do work"})
        self.mock_post.assert_called_once_with("tasks", data={"description": "Do work"})

    def test_update_puts_data(self):
        self.resource.update("task-1", {"description": "New desc"})
        self.mock_put.assert_called_once_with("tasks/task-1", data={"description": "New desc"})

    def test_delete_calls_delete(self):
        self.resource.delete("task-1")
        self.mock_delete.assert_called_once_with("tasks/task-1")

    def test_archive_calls_bulk(self):
        self.resource.archive(["task-1"])
        self.mock_bulk.assert_called_once_with("tasks", "archive", ["task-1"])

    def test_restore_calls_bulk(self):
        self.resource.restore(["task-1"])
        self.mock_bulk.assert_called_once_with("tasks", "restore", ["task-1"])

    def test_start_calls_bulk(self):
        self.resource.start("task-1")
        self.mock_bulk.assert_called_once_with("tasks", "start", ["task-1"])

    def test_stop_calls_bulk(self):
        self.resource.stop("task-1")
        self.mock_bulk.assert_called_once_with("tasks", "stop", ["task-1"])


# ---------------------------------------------------------------------------
# VendorResource Tests
# ---------------------------------------------------------------------------

class TestVendorResource(ResourceTestBase):

    def setUp(self):
        super().setUp()
        self.resource = VendorResource(self.session)

    def test_list_calls_get(self):
        self.resource.list()
        self.mock_get.assert_called_once()

    def test_get_calls_correct_path(self):
        self.resource.get("v-1")
        self.mock_get.assert_called_once_with("vendors/v-1")

    def test_create_posts_data(self):
        self.resource.create({"name": "Vendor Co"})
        self.mock_post.assert_called_once_with("vendors", data={"name": "Vendor Co"})

    def test_update_puts_data(self):
        self.resource.update("v-1", {"name": "New Vendor"})
        self.mock_put.assert_called_once_with("vendors/v-1", data={"name": "New Vendor"})

    def test_delete_calls_delete(self):
        self.resource.delete("v-1")
        self.mock_delete.assert_called_once_with("vendors/v-1")

    def test_archive_calls_bulk(self):
        self.resource.archive(["v-1", "v-2"])
        self.mock_bulk.assert_called_once_with("vendors", "archive", ["v-1", "v-2"])

    def test_restore_calls_bulk(self):
        self.resource.restore(["v-1"])
        self.mock_bulk.assert_called_once_with("vendors", "restore", ["v-1"])


# ---------------------------------------------------------------------------
# ExpenseResource Tests
# ---------------------------------------------------------------------------

class TestExpenseResource(ResourceTestBase):

    def setUp(self):
        super().setUp()
        self.resource = ExpenseResource(self.session)

    def test_list_calls_get(self):
        self.resource.list()
        self.mock_get.assert_called_once()

    def test_list_with_filters(self):
        self.resource.list(client_id="c-1", vendor_id="v-1")
        args, kwargs = self.mock_get.call_args
        self.assertEqual(kwargs["params"]["client_id"], "c-1")
        self.assertEqual(kwargs["params"]["vendor_id"], "v-1")

    def test_get_calls_correct_path(self):
        self.resource.get("exp-1")
        self.mock_get.assert_called_once_with("expenses/exp-1")

    def test_create_posts_data(self):
        data = {"amount": 50.0, "vendor_id": "v-1"}
        self.resource.create(data)
        self.mock_post.assert_called_once_with("expenses", data=data)

    def test_update_puts_data(self):
        self.resource.update("exp-1", {"amount": 75.0})
        self.mock_put.assert_called_once_with("expenses/exp-1", data={"amount": 75.0})

    def test_delete_calls_delete(self):
        self.resource.delete("exp-1")
        self.mock_delete.assert_called_once_with("expenses/exp-1")

    def test_archive_calls_bulk(self):
        self.resource.archive(["exp-1"])
        self.mock_bulk.assert_called_once_with("expenses", "archive", ["exp-1"])

    def test_restore_calls_bulk(self):
        self.resource.restore(["exp-1"])
        self.mock_bulk.assert_called_once_with("expenses", "restore", ["exp-1"])


# ---------------------------------------------------------------------------
# CreditResource Tests
# ---------------------------------------------------------------------------

class TestCreditResource(ResourceTestBase):

    def setUp(self):
        super().setUp()
        self.resource = CreditResource(self.session)

    def test_list_calls_get(self):
        self.resource.list()
        self.mock_get.assert_called_once()

    def test_get_calls_correct_path(self):
        self.resource.get("cr-1")
        self.mock_get.assert_called_once_with("credits/cr-1")

    def test_create_posts_data(self):
        data = {"client_id": "c-1", "line_items": []}
        self.resource.create(data)
        self.mock_post.assert_called_once_with("credits", data=data)

    def test_archive_calls_bulk(self):
        self.resource.archive(["cr-1"])
        self.mock_bulk.assert_called_once_with("credits", "archive", ["cr-1"])

    def test_restore_calls_bulk(self):
        self.resource.restore(["cr-1"])
        self.mock_bulk.assert_called_once_with("credits", "restore", ["cr-1"])


# ---------------------------------------------------------------------------
# RecurringInvoiceResource Tests
# ---------------------------------------------------------------------------

class TestRecurringInvoiceResource(ResourceTestBase):

    def setUp(self):
        super().setUp()
        self.resource = RecurringInvoiceResource(self.session)

    def test_list_calls_get(self):
        self.resource.list()
        self.mock_get.assert_called_once()

    def test_get_calls_correct_path(self):
        self.resource.get("ri-1")
        self.mock_get.assert_called_once_with("recurring_invoices/ri-1")

    def test_start_calls_bulk(self):
        self.resource.start("ri-1")
        self.mock_bulk.assert_called_once_with("recurring_invoices", "start", ["ri-1"])

    def test_stop_calls_bulk(self):
        self.resource.stop("ri-1")
        self.mock_bulk.assert_called_once_with("recurring_invoices", "stop", ["ri-1"])

    def test_archive_calls_bulk(self):
        self.resource.archive(["ri-1"])
        self.mock_bulk.assert_called_once_with("recurring_invoices", "archive", ["ri-1"])


# ---------------------------------------------------------------------------
# PurchaseOrderResource Tests
# ---------------------------------------------------------------------------

class TestPurchaseOrderResource(ResourceTestBase):

    def setUp(self):
        super().setUp()
        self.resource = PurchaseOrderResource(self.session)

    def test_list_calls_get(self):
        self.resource.list()
        self.mock_get.assert_called_once()

    def test_get_calls_correct_path(self):
        self.resource.get("po-1")
        self.mock_get.assert_called_once_with("purchase_orders/po-1")

    def test_send_calls_bulk_email(self):
        self.resource.send("po-1")
        self.mock_bulk.assert_called_once_with("purchase_orders", "email", ["po-1"])

    def test_archive_calls_bulk(self):
        self.resource.archive(["po-1"])
        self.mock_bulk.assert_called_once_with("purchase_orders", "archive", ["po-1"])


# ---------------------------------------------------------------------------
# Output Tests
# ---------------------------------------------------------------------------

class TestFormatOutput(unittest.TestCase):

    def _capture(self, func, *args, **kwargs) -> str:
        """Capture stdout from a function call."""
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            func(*args, **kwargs)
        return buf.getvalue()

    def test_json_mode_prints_json(self):
        data = {"data": [{"id": "1", "name": "Acme"}]}
        output = self._capture(format_output, data, json_mode=True)
        parsed = json.loads(output)
        self.assertEqual(parsed, data)

    def test_table_mode_clients(self):
        data = {
            "data": [
                {
                    "name": "Acme Corp",
                    "email": "a@b.com",
                    "balance": "1000.00",
                    "paid_to_date": "500.00",
                    "phone": "555-1234",
                }
            ]
        }
        output = self._capture(format_output, data, entity="clients")
        self.assertIn("Acme Corp", output)
        self.assertIn("a@b.com", output)

    def test_table_mode_invoices(self):
        data = {
            "data": [
                {
                    "number": "INV-001",
                    "client_name": "Acme",
                    "date": "2024-01-01",
                    "due_date": "2024-02-01",
                    "amount": "1000.00",
                    "balance": "1000.00",
                    "status_id": "2",
                }
            ]
        }
        output = self._capture(format_output, data, entity="invoices")
        self.assertIn("INV-001", output)
        self.assertIn("Acme", output)
        # Status should be humanized
        self.assertIn("Sent", output)

    def test_table_mode_products(self):
        data = {
            "data": [
                {
                    "product_key": "SKU-001",
                    "notes": "Widget",
                    "price": "9.99",
                    "quantity": "1",
                }
            ]
        }
        output = self._capture(format_output, data, entity="products")
        self.assertIn("SKU-001", output)
        self.assertIn("Widget", output)

    def test_empty_records(self):
        output = self._capture(format_output, {"data": []}, entity="clients")
        self.assertIn("no records", output)

    def test_single_record_dict_unwrap(self):
        data = {"data": {"id": "c-1", "name": "Solo"}}
        output = self._capture(format_output, data, entity="clients")
        self.assertIn("Solo", output)

    def test_list_of_dicts_direct(self):
        data = [{"name": "A", "email": "a@b.com", "balance": "0", "paid_to_date": "0", "phone": ""}]
        output = self._capture(format_output, data, entity="clients")
        self.assertIn("A", output)

    def test_json_mode_list(self):
        data = [{"id": "1"}]
        output = self._capture(format_output, data, json_mode=True)
        parsed = json.loads(output)
        self.assertEqual(parsed, data)

    def test_invoice_status_paid(self):
        data = {
            "data": [{
                "number": "INV-002",
                "client_name": "Corp",
                "date": "2024-01-01",
                "due_date": "2024-02-01",
                "amount": "500",
                "balance": "0",
                "status_id": "4",
            }]
        }
        output = self._capture(format_output, data, entity="invoices")
        self.assertIn("Paid", output)

    def test_no_entity_falls_back_to_first_keys(self):
        data = {"data": [{"foo": "bar", "baz": "qux"}]}
        output = self._capture(format_output, data)
        # Should output something without crashing
        self.assertIsInstance(output, str)


# ---------------------------------------------------------------------------
# CLI smoke tests (using Click's test runner)
# ---------------------------------------------------------------------------

class TestCLISmoke(unittest.TestCase):
    """Smoke-test the Click CLI wiring without real API calls."""

    def setUp(self):
        from click.testing import CliRunner
        from invoiceninja_cli.invoiceninja_cli import cli
        self.runner = CliRunner()
        self.cli = cli

    def test_help_exits_zero(self):
        result = self.runner.invoke(self.cli, ["--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("InvoiceNinja", result.output)

    def test_version_flag(self):
        result = self.runner.invoke(self.cli, ["--version"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("0.1.0", result.output)

    def test_clients_help(self):
        result = self.runner.invoke(self.cli, ["clients", "--help"])
        self.assertEqual(result.exit_code, 0)

    def test_invoices_help(self):
        result = self.runner.invoke(self.cli, ["invoices", "--help"])
        self.assertEqual(result.exit_code, 0)

    def test_missing_config_exits_nonzero(self):
        """Running a command without config should exit non-zero."""
        import tempfile, os
        from invoiceninja_cli.utils import config as cfg_mod
        orig_file = cfg_mod.CONFIG_FILE
        orig_dir = cfg_mod.CONFIG_DIR
        try:
            tmpdir = tempfile.mkdtemp()
            cfg_mod.CONFIG_DIR = Path(tmpdir)
            cfg_mod.CONFIG_FILE = Path(tmpdir) / "config.json"
            env = {k: v for k, v in os.environ.items()
                   if k not in ("INVOICENINJA_URL", "INVOICENINJA_TOKEN")}
            with patch.dict(os.environ, env, clear=True):
                result = self.runner.invoke(self.cli, ["clients", "list"])
            self.assertNotEqual(result.exit_code, 0)
        finally:
            cfg_mod.CONFIG_FILE = orig_file
            cfg_mod.CONFIG_DIR = orig_dir
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_ping_with_mocked_session(self):
        with patch("invoiceninja_cli.invoiceninja_cli._make_session") as mock_sess:
            sess = MagicMock()
            sess.ping.return_value = {"data": []}
            mock_sess.return_value = sess
            result = self.runner.invoke(self.cli, ["ping"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("successful", result.output)

    def test_clients_list_with_mocked_session(self):
        with patch("invoiceninja_cli.invoiceninja_cli._make_session") as mock_sess:
            sess = MagicMock()
            sess.get.return_value = {"data": [
                {"name": "Test Client", "email": "t@t.com", "balance": "0",
                 "paid_to_date": "0", "phone": ""}
            ]}
            mock_sess.return_value = sess
            result = self.runner.invoke(self.cli, ["clients", "list"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Test Client", result.output)

    def test_clients_list_json_flag(self):
        with patch("invoiceninja_cli.invoiceninja_cli._make_session") as mock_sess:
            sess = MagicMock()
            sess.get.return_value = {"data": [{"name": "A", "id": "1"}]}
            mock_sess.return_value = sess
            result = self.runner.invoke(self.cli, ["clients", "list", "--json"])
            self.assertEqual(result.exit_code, 0)
            parsed = json.loads(result.output)
            self.assertIsInstance(parsed, dict)

    def test_invoices_list_with_status_filter(self):
        with patch("invoiceninja_cli.invoiceninja_cli._make_session") as mock_sess:
            sess = MagicMock()
            sess.get.return_value = {"data": []}
            mock_sess.return_value = sess
            result = self.runner.invoke(self.cli, ["invoices", "list", "--status", "paid"])
            self.assertEqual(result.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
