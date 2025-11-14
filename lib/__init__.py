"""Shared library modules for Odoo integration scripts."""

from .odoo_client import OdooClient
from .phone_utils import format_phone_number, normalize_phone_for_query
from .rate_limiter import RateLimiter

__all__ = [
    'OdooClient',
    'format_phone_number',
    'normalize_phone_for_query',
    'RateLimiter',
]
