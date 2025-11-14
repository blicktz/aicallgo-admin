"""Odoo API client using JSON-RPC protocol."""

import json
import logging
from typing import Dict, List, Optional, Any

import requests


logger = logging.getLogger(__name__)


class OdooClient:
    """Client for interacting with Odoo via JSON-RPC API.

    This client handles authentication and common CRUD operations
    on Odoo models using the JSON-RPC protocol.

    Example:
        >>> client = OdooClient(
        ...     url="https://odoo.julya.ai",
        ...     db="odoo",
        ...     username="admin",
        ...     password="secret"
        ... )
        >>> client.authenticate()
        >>> contacts = client.search_read(
        ...     'res.partner',
        ...     [('phone', '=', '555-123-4567')],
        ...     fields=['id', 'name', 'email', 'phone']
        ... )
    """

    def __init__(self, url: str, db: str, username: str, password: str, timeout: int = 120):
        """Initialize Odoo client.

        Args:
            url: Odoo instance URL (e.g., https://odoo.julya.ai)
            db: Database name
            username: Odoo username
            password: Odoo password
            timeout: Request timeout in seconds (default: 120)
        """
        self.url = url.rstrip('/')
        self.db = db
        self.username = username
        self.password = password
        self.timeout = timeout
        self.uid: Optional[int] = None
        self.jsonrpc_url = f"{self.url}/jsonrpc"

    def _call_jsonrpc(self, service: str, method: str, *args) -> Any:
        """Make a JSON-RPC call to Odoo.

        Args:
            service: Service name ('common' or 'object')
            method: Method to call
            *args: Method arguments

        Returns:
            Response result

        Raises:
            requests.exceptions.RequestException: On network errors
            Exception: On Odoo errors
        """
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": service,
                "method": method,
                "args": list(args)
            },
            "id": 1
        }

        logger.debug(f"JSON-RPC call: {service}.{method}")

        response = requests.post(
            self.jsonrpc_url,
            json=payload,
            timeout=self.timeout,
            headers={"Content-Type": "application/json"}
        )

        response.raise_for_status()

        result = response.json()

        if "error" in result:
            error_data = result["error"]
            error_msg = error_data.get("data", {}).get("message", str(error_data))
            raise Exception(f"Odoo error: {error_msg}")

        return result.get("result")

    def authenticate(self) -> int:
        """Authenticate with Odoo and get UID.

        Returns:
            User ID (UID)

        Raises:
            Exception: If authentication fails
        """
        logger.info(f"Authenticating with Odoo as {self.username}")

        self.uid = self._call_jsonrpc(
            "common",
            "authenticate",
            self.db,
            self.username,
            self.password,
            {}
        )

        if not self.uid:
            raise Exception("Authentication failed: Invalid credentials")

        logger.info(f"Successfully authenticated with UID: {self.uid}")
        return self.uid

    def execute_kw(self, model: str, method: str, args: List = None, kwargs: Dict = None) -> Any:
        """Execute a method on an Odoo model.

        Args:
            model: Model name (e.g., 'res.partner')
            method: Method to execute (e.g., 'search', 'read', 'write')
            args: Positional arguments for the method
            kwargs: Keyword arguments for the method

        Returns:
            Method result

        Raises:
            Exception: If not authenticated or on Odoo errors
        """
        if not self.uid:
            raise Exception("Not authenticated. Call authenticate() first.")

        args = args or []
        kwargs = kwargs or {}

        return self._call_jsonrpc(
            "object",
            "execute_kw",
            self.db,
            self.uid,
            self.password,
            model,
            method,
            args,
            kwargs
        )

    def search(
        self,
        model: str,
        domain: List,
        offset: int = 0,
        limit: Optional[int] = None,
        order: Optional[str] = None
    ) -> List[int]:
        """Search for record IDs matching domain.

        Args:
            model: Model name (e.g., 'res.partner')
            domain: Search domain (e.g., [('phone', '=', '555-123-4567')])
            offset: Number of records to skip
            limit: Maximum number of records to return
            order: Sort order (e.g., 'name ASC')

        Returns:
            List of record IDs
        """
        kwargs = {'offset': offset}
        if limit is not None:
            kwargs['limit'] = limit
        if order:
            kwargs['order'] = order

        logger.debug(f"Searching {model} with domain: {domain}")

        return self.execute_kw(model, 'search', [domain], kwargs)

    def read(
        self,
        model: str,
        ids: List[int],
        fields: Optional[List[str]] = None
    ) -> List[Dict]:
        """Read records by IDs.

        Args:
            model: Model name
            ids: List of record IDs
            fields: List of field names to read (None for all fields)

        Returns:
            List of record dictionaries
        """
        kwargs = {}
        if fields:
            kwargs['fields'] = fields

        logger.debug(f"Reading {model} records: {ids}")

        return self.execute_kw(model, 'read', [ids], kwargs)

    def search_read(
        self,
        model: str,
        domain: List,
        fields: Optional[List[str]] = None,
        offset: int = 0,
        limit: Optional[int] = None,
        order: Optional[str] = None
    ) -> List[Dict]:
        """Search and read records in one call.

        Args:
            model: Model name (e.g., 'res.partner')
            domain: Search domain (e.g., [('phone', '=', '555-123-4567')])
            fields: List of field names to read (None for all fields)
            offset: Number of records to skip
            limit: Maximum number of records to return
            order: Sort order

        Returns:
            List of record dictionaries
        """
        kwargs = {'offset': offset}
        if fields:
            kwargs['fields'] = fields
        if limit is not None:
            kwargs['limit'] = limit
        if order:
            kwargs['order'] = order

        logger.debug(f"Search-read {model} with domain: {domain}")

        return self.execute_kw(model, 'search_read', [domain], kwargs)

    def create(self, model: str, values: Dict) -> int:
        """Create a new record.

        Args:
            model: Model name
            values: Dictionary of field values

        Returns:
            ID of created record
        """
        logger.debug(f"Creating {model} record")

        return self.execute_kw(model, 'create', [values])

    def write(self, model: str, ids: List[int], values: Dict) -> bool:
        """Update existing records.

        Args:
            model: Model name
            ids: List of record IDs to update
            values: Dictionary of field values to update

        Returns:
            True if successful
        """
        logger.debug(f"Updating {model} records: {ids}")

        return self.execute_kw(model, 'write', [ids, values])

    def unlink(self, model: str, ids: List[int]) -> bool:
        """Delete records.

        Args:
            model: Model name
            ids: List of record IDs to delete

        Returns:
            True if successful
        """
        logger.debug(f"Deleting {model} records: {ids}")

        return self.execute_kw(model, 'unlink', [ids])

    def search_count(self, model: str, domain: List) -> int:
        """Count records matching domain.

        Args:
            model: Model name
            domain: Search domain

        Returns:
            Number of matching records
        """
        logger.debug(f"Counting {model} with domain: {domain}")

        return self.execute_kw(model, 'search_count', [domain])

    # Tag convenience methods (delegate to OdooTagManager)
    def get_tag_manager(self):
        """Get a tag manager instance for this client.

        Returns:
            OdooTagManager instance

        Note:
            Import is done locally to avoid circular dependencies
        """
        from lib.tag_manager import OdooTagManager
        return OdooTagManager(self)

    def get_or_create_tag(self, name: str) -> int:
        """Get existing tag or create if it doesn't exist.

        Convenience method that creates a tag manager and calls get_or_create_tag.

        Args:
            name: Tag name

        Returns:
            Tag ID
        """
        tag_manager = self.get_tag_manager()
        return tag_manager.get_or_create_tag(name)

    def get_tags_by_names(self, names: List[str]) -> Dict[str, int]:
        """Get or create multiple tags by name.

        Convenience method that creates a tag manager and calls get_tags_by_names.

        Args:
            names: List of tag names

        Returns:
            Dictionary mapping tag names to tag IDs
        """
        tag_manager = self.get_tag_manager()
        return tag_manager.get_tags_by_names(names)
