"""CSV parser and validator for cold call contact lists."""
import io
from typing import List, Dict, Tuple, Optional
import pandas as pd
import streamlit as st


def validate_csv(uploaded_file) -> Tuple[bool, Optional[str]]:
    """Validate CSV file format and required columns.

    Args:
        uploaded_file: Streamlit UploadedFile object

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Read CSV
        df = pd.read_csv(uploaded_file)

        # Reset file pointer for subsequent reads
        uploaded_file.seek(0)

        # Check if empty
        if df.empty:
            return False, "CSV file is empty"

        # Required columns
        required_columns = {'name', 'company', 'phone'}
        missing_columns = required_columns - set(df.columns.str.lower())

        if missing_columns:
            return False, f"Missing required columns: {', '.join(missing_columns)}"

        # Check for at least one row of data
        if len(df) == 0:
            return False, "CSV has no contact rows"

        # Validate phone column is not all empty
        phone_col = next((col for col in df.columns if col.lower() == 'phone'), None)
        if phone_col and df[phone_col].isna().all():
            return False, "Phone column has no valid numbers"

        return True, None

    except pd.errors.EmptyDataError:
        return False, "CSV file is empty"
    except pd.errors.ParserError as e:
        return False, f"CSV parsing error: {str(e)}"
    except Exception as e:
        return False, f"Error validating CSV: {str(e)}"


def parse_contacts(uploaded_file) -> List[Dict[str, str]]:
    """Parse CSV file and extract contact information.

    Args:
        uploaded_file: Streamlit UploadedFile object

    Returns:
        List of contact dictionaries with normalized column names

    Raises:
        ValueError: If CSV is invalid or parsing fails
    """
    try:
        # Validate first
        is_valid, error = validate_csv(uploaded_file)
        if not is_valid:
            raise ValueError(error)

        # Read CSV
        df = pd.read_csv(uploaded_file)

        # Normalize column names to lowercase
        df.columns = df.columns.str.lower().str.strip()

        # Extract contacts
        contacts = []
        for idx, row in df.iterrows():
            contact = {
                'name': str(row.get('name', '')).strip(),
                'company': str(row.get('company', '')).strip(),
                'phone': str(row.get('phone', '')).strip(),
                'title': str(row.get('title', '')).strip() if 'title' in df.columns else '',
                'status': 'pending',  # Initial status
                'notes': '',  # Empty notes
                'call_outcome': '',  # Empty outcome
            }

            # Skip rows with missing critical data
            if not contact['name'] or not contact['phone']:
                continue

            contacts.append(contact)

        if not contacts:
            raise ValueError("No valid contacts found in CSV")

        return contacts

    except Exception as e:
        st.error(f"Error parsing CSV: {str(e)}")
        raise


def display_contacts_table(contacts: List[Dict[str, str]]) -> None:
    """Display contacts in a formatted table.

    Args:
        contacts: List of contact dictionaries
    """
    if not contacts:
        st.warning("No contacts to display")
        return

    # Create DataFrame for display
    df = pd.DataFrame(contacts)

    # Select columns to display
    display_columns = ['name', 'company', 'phone', 'title', 'status']
    display_df = df[display_columns].copy()

    # Rename columns for better display
    display_df.columns = ['Name', 'Company', 'Phone', 'Title', 'Status']

    # Display with formatting
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            'Name': st.column_config.TextColumn('Name', width='medium'),
            'Company': st.column_config.TextColumn('Company', width='medium'),
            'Phone': st.column_config.TextColumn('Phone', width='medium'),
            'Title': st.column_config.TextColumn('Title', width='medium'),
            'Status': st.column_config.TextColumn('Status', width='small'),
        }
    )


def get_contact_by_index(contacts: List[Dict[str, str]], index: int) -> Optional[Dict[str, str]]:
    """Get a contact by index.

    Args:
        contacts: List of contact dictionaries
        index: Contact index

    Returns:
        Contact dictionary or None if index out of range
    """
    if 0 <= index < len(contacts):
        return contacts[index]
    return None


def update_contact_status(contacts: List[Dict[str, str]], index: int,
                          status: str, outcome: str = '', notes: str = '') -> None:
    """Update contact status and call outcome.

    Args:
        contacts: List of contact dictionaries
        index: Contact index
        status: New status (e.g., 'calling', 'completed', 'failed')
        outcome: Call outcome (e.g., 'connected', 'voicemail', 'no_answer')
        notes: Call notes
    """
    if 0 <= index < len(contacts):
        contacts[index]['status'] = status
        contacts[index]['call_outcome'] = outcome
        contacts[index]['notes'] = notes
