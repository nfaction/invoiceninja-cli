"""Core resource modules for invoiceninja-cli."""

from .session import InvoiceNinjaSession, InvoiceNinjaAPIError
from .clients import ClientResource
from .invoices import InvoiceResource
from .quotes import QuoteResource
from .payments import PaymentResource
from .products import ProductResource
from .projects import ProjectResource
from .tasks import TaskResource
from .vendors import VendorResource
from .expenses import ExpenseResource
from .credits import CreditResource
from .recurring_invoices import RecurringInvoiceResource
from .purchase_orders import PurchaseOrderResource

__all__ = [
    "InvoiceNinjaSession",
    "InvoiceNinjaAPIError",
    "ClientResource",
    "InvoiceResource",
    "QuoteResource",
    "PaymentResource",
    "ProductResource",
    "ProjectResource",
    "TaskResource",
    "VendorResource",
    "ExpenseResource",
    "CreditResource",
    "RecurringInvoiceResource",
    "PurchaseOrderResource",
]
