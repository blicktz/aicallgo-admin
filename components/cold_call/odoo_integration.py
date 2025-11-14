"""
Odoo CRM Integration for Cold Call Dialer

This module handles all integration with Odoo CRM including:
- Loading contacts from saved searches/filters
- Dynamic status field integration
- Saving call notes to contact activity log

For complete documentation, see: docs/cold-call-dialer/odoo-integration-plan.md
"""

import os
import ast
import math
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import sys
import logging

# Add lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lib'))
from odoo_client import OdooClient

logger = logging.getLogger(__name__)


class OdooIntegration:
    """Handles all Odoo CRM integration for cold calling"""

    def __init__(self):
        self.client = None
        self.status_mapping = None
        self._initialize_client()
        self._load_field_definitions()

    def _initialize_client(self):
        """Initialize Odoo client with environment config"""
        odoo_url = os.getenv('ODOO_URL', 'https://odoo.julya.ai')
        odoo_db = os.getenv('ODOO_DB', 'odoo')
        odoo_username = os.getenv('ODOO_USERNAME')
        odoo_password = os.getenv('ODOO_PASSWORD')

        if not all([odoo_url, odoo_db, odoo_username, odoo_password]):
            logger.warning("Odoo credentials not configured. Integration disabled.")
            return

        try:
            self.client = OdooClient(
                url=odoo_url,
                db=odoo_db,
                username=odoo_username,
                password=odoo_password
            )
            self.client.authenticate()
            logger.info(f"Odoo client initialized successfully (URL: {odoo_url})")
        except Exception as e:
            logger.error(f"Failed to initialize Odoo client: {e}")
            self.client = None

    def _load_field_definitions(self):
        """Load x_cold_call_status field definition"""
        if not self.client:
            return

        try:
            field_info = self.client.execute_kw(
                'res.partner',
                'fields_get',
                [],
                {'allfields': ['x_cold_call_status']}
            )

            if 'x_cold_call_status' in field_info:
                selection = field_info['x_cold_call_status']['selection']

                self.status_mapping = {
                    'options': selection,  # [('value', 'Name'), ...]
                    'value_to_name': dict(selection),
                    'name_to_value': {name: value for value, name in selection}
                }
                logger.info(f"Loaded {len(selection)} status options from Odoo")
            else:
                logger.warning("x_cold_call_status field not found in Odoo")
                self.status_mapping = None

        except Exception as e:
            logger.error(f"Error loading field definitions: {e}")
            self.status_mapping = None

    def is_available(self) -> bool:
        """Check if Odoo integration is available"""
        return self.client is not None

    def get_available_filters(self) -> List[Dict]:
        """
        Get list of available contact filters

        Returns:
            List of filter dictionaries with id, name, domain, context
        """
        if not self.client:
            return []

        try:
            filters = self.client.search_read(
                'ir.filters',
                domain=[
                    ('model_id', '=', 'res.partner'),
                    ('user_id', 'in', [self.client.uid, False])
                ],
                fields=['id', 'name', 'domain', 'context'],
                order='name asc'
            )
            logger.info(f"Fetched {len(filters)} available filters")
            return filters
        except Exception as e:
            logger.error(f"Error fetching filters: {e}")
            return []

    def get_filter_contact_count(self, filter_id: int) -> int:
        """
        Get total number of contacts in a filter

        Args:
            filter_id: ID of the filter

        Returns:
            Total count of contacts matching the filter
        """
        if not self.client:
            return 0

        try:
            filter_record = self.client.read('ir.filters', [filter_id], ['domain'])[0]
            domain = ast.literal_eval(filter_record['domain'])
            count = self.client.search_count('res.partner', domain=domain)
            logger.info(f"Filter {filter_id} contains {count} contacts")
            return count
        except Exception as e:
            logger.error(f"Error counting contacts for filter {filter_id}: {e}")
            return 0

    def load_contacts_from_filter(
        self,
        filter_id: int,
        page: int = 1,
        page_size: int = 50
    ) -> Dict:
        """
        Load contacts from filter with pagination

        Args:
            filter_id: ID of the filter to load contacts from
            page: Page number (1-indexed)
            page_size: Number of contacts per page

        Returns:
            Dictionary with contacts, pagination info, and filter name
        """
        if not self.client:
            return {
                'contacts': [],
                'filter_name': '',
                'page': page,
                'page_size': page_size,
                'total': 0,
                'total_pages': 0,
                'error': 'Odoo integration not available'
            }

        try:
            # Get filter domain and name
            filter_record = self.client.read('ir.filters', [filter_id], ['domain', 'name'])[0]
            domain = ast.literal_eval(filter_record['domain'])

            # Get total count
            total = self.client.search_count('res.partner', domain=domain)

            # Calculate pagination
            offset = (page - 1) * page_size
            total_pages = math.ceil(total / page_size) if total > 0 else 0

            # Load contacts
            contacts = self.client.search_read(
                'res.partner',
                domain=domain,
                fields=[
                    'id', 'name', 'phone', 'mobile',
                    'company_name', 'function', 'x_cold_call_status',
                    'email', 'city', 'country_id', 'street', 'state_id',
                    'comment',  # Web crawled insights
                    # Custom fields
                    'x_phone_carrier_type',
                    'x_outbound_status_IVR', 'x_outbound_status_live',
                    'x_outbound_status_no_answer', 'x_outbound_status_voicemail',
                    'x_google_rating', 'x_google_review_count',
                    'x_is_julya_icp', 'x_is_valid_lead'
                ],
                limit=page_size,
                offset=offset,
                order='name asc'
            )

            # Format for admin-board
            formatted_contacts = []
            for c in contacts:
                # Prefer mobile over phone
                phone = c.get('mobile') or c.get('phone') or ''

                # Skip contacts without phone
                if not phone:
                    continue

                # Get current Odoo status display name
                current_status_value = c.get('x_cold_call_status', '')
                current_status_name = ''
                if current_status_value and self.status_mapping:
                    current_status_name = self.status_mapping['value_to_name'].get(
                        current_status_value, current_status_value
                    )

                # Format boolean fields as checkmarks
                def format_boolean(value):
                    if value is True:
                        return '✓'
                    elif value is False:
                        return '✗'
                    else:
                        return '-'

                # Format numeric fields
                def format_number(value, default=0):
                    if value is None or value == False:
                        return default
                    return int(value) if isinstance(value, (int, float)) else default

                formatted_contacts.append({
                    'odoo_id': c['id'],
                    'name': c.get('name', ''),
                    'company': c.get('company_name', ''),
                    'phone': phone,
                    'title': c.get('function', ''),
                    'email': c.get('email', ''),
                    'city': c.get('city', ''),
                    'country': c.get('country_id', [None, ''])[1] if c.get('country_id') else '',
                    'status': 'pending',
                    'notes': '',
                    'call_outcome': '',
                    'current_odoo_status': current_status_name,
                    # Address fields
                    'street': c.get('street', ''),
                    'state': c.get('state_id', [None, ''])[1] if c.get('state_id') else '',
                    # Web crawled insights
                    'comment': c.get('comment', ''),
                    # Custom fields
                    'carrier_type': c.get('x_phone_carrier_type', ''),
                    'is_valid_lead': format_boolean(c.get('x_is_valid_lead')),
                    'is_julya_icp': format_boolean(c.get('x_is_julya_icp')),
                    'google_rating': c.get('x_google_rating', 0),
                    'google_review_count': format_number(c.get('x_google_review_count')),
                    'outbound_ivr': format_number(c.get('x_outbound_status_IVR')),
                    'outbound_live': format_number(c.get('x_outbound_status_live')),
                    'outbound_no_answer': format_number(c.get('x_outbound_status_no_answer')),
                    'outbound_voicemail': format_number(c.get('x_outbound_status_voicemail'))
                })

            logger.info(
                f"Loaded {len(formatted_contacts)} contacts from filter '{filter_record['name']}' "
                f"(page {page}/{total_pages})"
            )

            return {
                'contacts': formatted_contacts,
                'filter_name': filter_record['name'],
                'page': page,
                'page_size': page_size,
                'total': total,
                'total_pages': total_pages
            }

        except Exception as e:
            logger.error(f"Error loading contacts from filter {filter_id}: {e}")
            return {
                'contacts': [],
                'filter_name': '',
                'page': page,
                'page_size': page_size,
                'total': 0,
                'total_pages': 0,
                'error': str(e)
            }

    def get_status_options(self) -> Optional[List[Tuple[str, str]]]:
        """
        Get available call status options

        Returns:
            List of tuples (value, display_name) or None if not available
        """
        if self.status_mapping:
            return self.status_mapping['options']
        return None

    def get_status_display_names(self) -> List[str]:
        """
        Get list of status display names for dropdown

        Returns:
            List of display names
        """
        if self.status_mapping:
            return [name for _, name in self.status_mapping['options']]
        return []

    def status_name_to_value(self, name: str) -> str:
        """
        Convert display name to Odoo value

        Args:
            name: Display name (e.g., "Meeting Booked")

        Returns:
            Odoo value (e.g., "meeting_booked")
        """
        if self.status_mapping:
            return self.status_mapping['name_to_value'].get(name, '')
        return ''

    def status_value_to_name(self, value: str) -> str:
        """
        Convert Odoo value to display name

        Args:
            value: Odoo value (e.g., "meeting_booked")

        Returns:
            Display name (e.g., "Meeting Booked")
        """
        if self.status_mapping:
            return self.status_mapping['value_to_name'].get(value, '')
        return ''

    def update_contact_status(self, odoo_id: int, status_value: str) -> bool:
        """
        Update contact's cold call status

        Args:
            odoo_id: Odoo contact ID
            status_value: Status value to set (not display name)

        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            logger.error("Cannot update status: Odoo client not available")
            return False

        try:
            self.client.write(
                'res.partner',
                [odoo_id],
                {'x_cold_call_status': status_value}
            )
            logger.info(f"Updated contact {odoo_id} status to '{status_value}'")
            return True
        except Exception as e:
            logger.error(f"Error updating contact {odoo_id} status: {e}")
            return False

    def create_call_note(
        self,
        odoo_id: int,
        outcome_name: str,
        duration: int,
        notes: str
    ) -> bool:
        """
        Create internal note on contact

        Args:
            odoo_id: Odoo contact ID
            outcome_name: Call outcome display name
            duration: Call duration in seconds
            notes: Call notes from user

        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            logger.error("Cannot create note: Odoo client not available")
            return False

        try:
            # Build plain text note with only user's notes
            body = notes if notes else '(No notes)'

            # Create note
            self.client.execute_kw(
                'res.partner',
                'message_post',
                [odoo_id],
                {
                    'body': body,
                    'message_type': 'comment'
                }
            )
            logger.info(f"Created call note for contact {odoo_id}")
            return True

        except Exception as e:
            logger.error(f"Error creating note for contact {odoo_id}: {e}")
            return False

    def complete_call(
        self,
        odoo_id: int,
        status_name: str,
        duration: int,
        notes: str
    ) -> Dict[str, any]:
        """
        Complete post-call actions: update status and create note

        Args:
            odoo_id: Odoo contact ID
            status_name: Call outcome display name
            duration: Call duration in seconds
            notes: Call notes from user

        Returns:
            Dictionary with success status and any errors
        """
        if not self.client:
            return {
                'success': False,
                'error': 'Odoo integration not available',
                'status_updated': False,
                'note_created': False
            }

        result = {
            'success': False,
            'status_updated': False,
            'note_created': False,
            'error': None
        }

        try:
            # Convert status name to value
            status_value = self.status_name_to_value(status_name)

            # Update status field
            if status_value:
                result['status_updated'] = self.update_contact_status(odoo_id, status_value)
            else:
                logger.warning(f"Could not map status name '{status_name}' to Odoo value")

            # Create activity note
            result['note_created'] = self.create_call_note(odoo_id, status_name, duration, notes)

            # Overall success if at least one operation succeeded
            result['success'] = result['status_updated'] or result['note_created']

            if result['success']:
                logger.info(
                    f"Completed call for contact {odoo_id}: "
                    f"status={'✓' if result['status_updated'] else '✗'}, "
                    f"note={'✓' if result['note_created'] else '✗'}"
                )

            return result

        except Exception as e:
            logger.error(f"Error completing call for contact {odoo_id}: {e}")
            result['error'] = str(e)
            return result

    def refresh_contact_statuses(self, odoo_ids: List[int]) -> Dict[int, str]:
        """
        Refresh status for multiple contacts from Odoo

        Args:
            odoo_ids: List of Odoo contact IDs

        Returns:
            Dictionary mapping odoo_id to current status display name
        """
        if not self.client or not odoo_ids:
            return {}

        try:
            contacts = self.client.read(
                'res.partner',
                odoo_ids,
                ['id', 'x_cold_call_status']
            )

            status_map = {}
            for contact in contacts:
                status_value = contact.get('x_cold_call_status', '')
                status_name = self.status_value_to_name(status_value) if status_value else ''
                status_map[contact['id']] = status_name

            logger.info(f"Refreshed status for {len(status_map)} contacts")
            return status_map

        except Exception as e:
            logger.error(f"Error refreshing contact statuses: {e}")
            return {}


# Singleton instance
_odoo_integration = None


def get_odoo_integration() -> OdooIntegration:
    """
    Get singleton instance of OdooIntegration

    Returns:
        OdooIntegration instance
    """
    global _odoo_integration
    if _odoo_integration is None:
        _odoo_integration = OdooIntegration()
    return _odoo_integration
