import streamlit as st
import pandas as pd
from datetime import datetime, date
import json
import hashlib
from typing import Dict
from pathlib import Path
from openpyxl import load_workbook
import time
from io import BytesIO
from openpyxl.styles import NamedStyle, Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter

def save_entries():
    """Save all log entries to a JSON file."""
    try:
        with open('log_entries.json', 'w') as f:
            json.dump(st.session_state.log_entries, f, default=str, indent=4)
        return True
    except Exception as e:
        st.error(f"Error saving entries: {str(e)}")
        return False

def validate_medicaid_id(medicaid_id: str) -> tuple[bool, str]:
    """
    Validate Medicaid ID format:
    - Must be 7 characters long
    - First character must be a letter
    - Can contain both letters and numbers
    Returns: (is_valid: bool, error_message: str)
    """
    if not medicaid_id:
        return False, "Medicaid ID is required"
    
    # Remove any spaces and special characters
    medicaid_id = medicaid_id.strip().upper()
    
    # Check length
    if len(medicaid_id) != 7:
        return False, "Medicaid ID must be exactly 7 characters long"
    
    # Check if first character is a letter
    if not medicaid_id[0].isalpha():
        return False, "Medicaid ID must start with a letter"
    
    # Check if remaining characters are alphanumeric
    if not medicaid_id[1:].isalnum():
        return False, "Medicaid ID can only contain letters and numbers"
    
    # If we reach here, the format is valid
    return True, ""


def get_member_details(medicaid_id: str) -> Dict:
    """
    Get member details from Excel file based on Medicaid ID.
    Returns a dictionary with member details or empty dict if not found.
    """
    try:
        # Load the Excel file - make sure to use the correct file path
        excel_path = './Master_db.xlsx'  # Update this to match your actual file name
        
        if not Path(excel_path).exists():
            st.error(f"Excel file not found at: {excel_path}")
            return {}
            
        # Read Excel file
        df = pd.read_excel(excel_path)
        
        # Convert MedicaidID to string and clean it
        df['MedicaidID'] = df['MedicaidID'].astype(str).str.strip()
        medicaid_id = str(medicaid_id).strip()
        
        # Find the member (case-insensitive comparison)
        member_mask = df['MedicaidID'].str.upper() == medicaid_id.upper()
        
        if not member_mask.any():
            return {}
            
        # Get the first matching row
        member_row = df[member_mask].iloc[0]
        
        # Create a dictionary with standardized keys
        member_dict = {
            'medicaid_id': medicaid_id,
            'member_name': member_row.get('FIRST NAME', '') + ' ' + member_row.get('LAST NAME', ''),
            'member_dob': member_row.get('DOB', None),
            'member_id': member_row.get('MEMBER ID', ''),
        }
        
        return member_dict
    except Exception as e:
        st.error(f"Error retrieving member details: {str(e)}")
        print(f"Error retrieving member details: {str(e)}")  # Debug log
        return {}

# Set page configuration
st.set_page_config(
    page_title="2025 Colorado Transition Coordinator Log Notes",
    page_icon="📝",
    layout="wide"
)

# Initialize session state for storing log entries
if 'log_entries' not in st.session_state:
    # Try to load existing entries from file
    try:
        with open('log_entries.json', 'r') as f:
            st.session_state.log_entries = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # If file doesn't exist or is invalid, start with empty list
        st.session_state.log_entries = []

# Initialize session state for sections
if 'current_section' not in st.session_state:
    st.session_state.current_section = 1

# Initialize session state for form data if not exists
if 'form_data' not in st.session_state:
    st.session_state.form_data = {}

# Initialize session state for member data
if 'member_data' not in st.session_state:
    st.session_state.member_data = {}

# Initialize session state for member verification
if 'member_verified' not in st.session_state:
    st.session_state.member_verified = False

# Initialize session state for new member flag
if 'new_member' not in st.session_state:
    st.session_state.new_member = False

# Add after other session state initializations
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

# Add these admin credentials (in practice, these should be stored securely, not in code)
ADMIN_CREDENTIALS: Dict[str, str] = {
    "admin": hashlib.sha256("admin123".encode()).hexdigest(),
    "supervisor": hashlib.sha256("super456".encode()).hexdigest()
}

# Define total number of sections
TOTAL_SECTIONS = 8

# Add CSS for reduced spacing and smaller fonts
st.markdown("""
<style>
/* Main title styling */
.main-title {
    font-size: 2rem !important;
    font-weight: bold !important;
    margin-bottom: 1rem !important;
    text-align: center !important;
}

/* Section headers */
h2, .subheader {
    font-size: 1.5rem !important;
    font-weight: bold !important;
    margin-top: 1rem !important;
    margin-bottom: 1rem !important;
}

/* Section numbers and labels */
.section-number {
    font-size: 1rem !important;
    font-weight: bold !important;
    margin-top: 0.5rem !important;
}

/* Form labels and text */
.stTextInput label, .stTextArea label, .stRadio label, .stSelectbox label, .stMultiSelect label {
    font-size: 0.9rem !important;
    font-weight: 500 !important;
}

/* Progress section text */
.progress-text {
    font-size: 1rem !important;
    margin-top: 0.25rem !important;
    margin-bottom: 0.75rem !important;
}

/* Step container adjustments */
.step-container {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin: 10px 0;
}

.step {
    width: 35px !important;
    height: 35px !important;
    border-radius: 50%;
    background-color: #E7E7E7;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    color: white;
    position: relative;
    font-size: 1rem !important;
}

.step.active {
    background-color: #0096FF;
}

.step.completed {
    background-color: #0096FF;
}

.step-line {
    flex-grow: 1;
    height: 2px;
    background-color: #E7E7E7;
    margin: 0 5px;
}

.step-line.completed {
    background-color: #0096FF;
}

/* Additional spacing adjustments */
.stForm [data-testid="stForm"] {
    padding-top: 0.5rem !important;
}

.stRadio > div {
    margin-bottom: 0.5rem !important;
}

div.row-widget.stRadio > div {
    gap: 0.5rem !important;
}
</style>
""", unsafe_allow_html=True)

# Add CSS for top navigation bar
st.markdown("""
<style>
    /* Top navigation bar styling */
    .top-nav {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.5rem 1rem;
        background-color: #f8f9fa;
        border-bottom: 1px solid #dee2e6;
        margin-bottom: 1rem;
    }
    
    .nav-logo {
        flex: 0 0 200px;
    }
    
    .nav-links {
        display: flex;
        gap: 1rem;
    }
    
    .nav-button {
        background-color: transparent;
        border: none;
        padding: 0.5rem 1rem;
        cursor: pointer;
        font-weight: 500;
        border-radius: 4px;
    }
    
    .nav-button:hover {
        background-color: #e9ecef;
    }
    
    .nav-button.active {
        background-color: #0096FF;
        color: white;
    }
    
    /* Admin dropdown menu */
    .admin-dropdown {
        position: relative;
        display: inline-block;
    }
    
    .admin-dropdown-content {
        display: none;
        position: absolute;
        background-color: #f9f9f9;
        min-width: 160px;
        box-shadow: 0px 8px 16px 0px rgba(0,0,0,0.2);
        z-index: 1;
        right: 0;
    }
    
    .admin-dropdown-content a {
        color: black;
        padding: 12px 16px;
        text-decoration: none;
        display: block;
    }
    
    .admin-dropdown-content a:hover {
        background-color: #f1f1f1;
    }
    
    .admin-dropdown:hover .admin-dropdown-content {
        display: block;
    }
    
    /* Hide the default sidebar */
    [data-testid="stSidebar"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# Initialize nav_selection if not in session state
if 'nav_selection' not in st.session_state:
    st.session_state.nav_selection = "Member Login"  # Changed from "Submit New Form"

# Create a row for the navigation bar
nav_row = st.container()

with nav_row:
    # Create two columns - one for logo, one for buttons
    logo_col, buttons_col = st.columns([1, 3])
    
    with logo_col:
        # Display the logo
        st.image("https://focuscares.com/wp-content/uploads/elementor/thumbs/logo-pcsu71jmplrr1f3b7mtv083rbyula7p5imfik70y8o.png", width=150)
    
    with buttons_col:
        # Create a horizontal container for the buttons, aligned to the right
        button_cols = st.columns([3, 1, 1, 1])  # First column is empty space to push buttons right
        
        with button_cols[1]:
            if st.button("Member Login", 
                        type="primary" if st.session_state.nav_selection == "Member Login" else "secondary",
                        use_container_width=True):
                st.session_state.nav_selection = "Member Login"
                st.session_state.admin_selection = None
                st.rerun()
        
        with button_cols[2]:
            if st.button("Support", 
                        type="primary" if st.session_state.nav_selection == "Support" else "secondary",
                        use_container_width=True):
                st.session_state.nav_selection = "Support"
                st.session_state.admin_selection = None
                st.rerun()
        
        with button_cols[3]:
            if st.button("Admin", 
                        type="primary" if st.session_state.nav_selection == "Admin" else "secondary",
                        use_container_width=True):
                st.session_state.nav_selection = "Admin"
                st.session_state.admin_selection = None
                st.rerun()

# Add a separator line
st.markdown("<hr style='margin-top: 0; margin-bottom: 1rem;'>", unsafe_allow_html=True)

# Show admin sub-navigation if Admin is selected and user is admin
if st.session_state.nav_selection == "Admin" and st.session_state.is_admin:
    admin_row = st.container()
    with admin_row:
        # Create columns with the same alignment as content
        admin_cols = st.columns(3)
        
        with admin_cols[0]:
            if st.button("View Forms", key="view_forms", use_container_width=True):
                st.session_state.admin_selection = "View Submitted Forms"
                st.rerun()
        
        
        with admin_cols[1]:
            if st.button("Process Claims", key="process_claims", use_container_width=True):
                st.session_state.admin_selection = "Process Claims"
                st.rerun()

        with admin_cols[2]:
            if st.button("Payroll", key="pay_roll", use_container_width=True):
                st.session_state.admin_selection = "Payroll"
                st.rerun()
        

# Add another separator line after admin sub-navigation if needed
if st.session_state.nav_selection == "Admin" and st.session_state.is_admin:
    st.markdown("<hr style='margin-top: 0.5rem; margin-bottom: 1rem;'>", unsafe_allow_html=True)

# Add this code to handle the admin selections
if st.session_state.nav_selection == "Admin" and st.session_state.is_admin:
    if st.session_state.get('admin_selection') == "View Submitted Forms":
        st.markdown('<h2 class="subheader">View Submitted Forms</h2>', unsafe_allow_html=True)
        
        # Load log entries
        try:
            with open('log_entries.json', 'r') as f:
                log_entries = json.load(f)
            
            if log_entries:
                # Create filters
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # Get unique Medicaid IDs
                    medicaid_ids = sorted(list(set(entry.get('medicaid_id', '') for entry in log_entries if 'medicaid_id' in entry)))
                    selected_medicaid_id = st.selectbox("Filter by Medicaid ID", ["All"] + medicaid_ids)
                
                with col2:
                    # Get unique note categories
                    note_categories = sorted(list(set(entry.get('note_category', '') for entry in log_entries if 'note_category' in entry)))
                    selected_category = st.selectbox("Filter by Note Category", ["All"] + note_categories)
                
                with col3:
                    # Date range filter
                    date_range = st.date_input(
                        "Filter by Date Range",
                        value=(datetime.now().date() - pd.Timedelta(days=30), datetime.now().date()),
                        max_value=datetime.now().date()
                    )
                
                # Apply filters
                filtered_entries = log_entries
                
                # Filter by Medicaid ID
                if selected_medicaid_id != "All":
                    filtered_entries = [entry for entry in filtered_entries if entry.get('medicaid_id') == selected_medicaid_id]
                
                # Filter by note category
                if selected_category != "All":
                    filtered_entries = [entry for entry in filtered_entries if entry.get('note_category') == selected_category]
                
                # Filter by date range
                if len(date_range) == 2:
                    start_date, end_date = date_range
                    filtered_entries = [
                        entry for entry in filtered_entries 
                        if start_date <= datetime.strptime(entry.get('service_date', '1900-01-01'), '%Y-%m-%d').date() <= end_date
                    ]
                
                # Create a DataFrame for display
                if filtered_entries:
                    # Extract key fields for the table
                    table_data = []
                    for entry in filtered_entries:
                        table_data.append({
                            'Timestamp': entry.get('timestamp', ''),
                            'Medicaid ID': entry.get('medicaid_id', ''),
                            'Member Name': entry.get('member_name', ''),
                            'Service Date': entry.get('service_date', ''),
                            'Note Category': entry.get('note_category', ''),
                            'TCM Hours': entry.get('tcm_hours', 0) if 'tcm_hours' in entry else 0,
                            'Travel Time': entry.get('travel_time', 0) if 'travel_time' in entry else 0
                        })
                    
                    df = pd.DataFrame(table_data)
                    
                    # Display the table
                    st.dataframe(df, use_container_width=True)
                    
                    # Add export button
                    if st.button("Export to Excel"):
                        # Create Excel file in memory
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            df.to_excel(writer, index=False, sheet_name='Form Submissions')
                            
                            # Access the workbook and the worksheet
                            workbook = writer.book
                            worksheet = writer.sheets['Form Submissions']
                            
                            # Define styles
                            header_style = NamedStyle(name='header_style')
                            header_style.font = Font(bold=True, color='FFFFFF')
                            header_style.fill = PatternFill(start_color='4F81BD', end_color='4F81BD', fill_type='solid')
                            header_style.alignment = Alignment(horizontal='center', vertical='center')
                            
                            # Apply styles to header row
                            for col_num, column_title in enumerate(df.columns, 1):
                                cell = worksheet.cell(row=1, column=col_num)
                                cell.style = header_style
                            
                            # Adjust column widths
                            for idx, col in enumerate(df.columns):
                                column_letter = get_column_letter(idx + 1)
                                column_width = max(len(str(col)), df[col].astype(str).map(len).max())
                                worksheet.column_dimensions[column_letter].width = column_width + 2
                        
                        # Set up download button
                        output.seek(0)
                        st.download_button(
                            label="Download Excel file",
                            data=output.getvalue(),
                            file_name=f"form_submissions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    
                    # # Add view details functionality
                    # st.markdown("### View Form Details")
                    # selected_entry_idx = st.selectbox(
                    #     "Select a form to view details",
                    #     options=range(len(filtered_entries)),
                    #     format_func=lambda i: f"{filtered_entries[i].get('member_name', '')} - {filtered_entries[i].get('service_date', '')} ({filtered_entries[i].get('note_category', '')})"
                    # )
                    
                    if st.button("View Details"):
                        selected_entry = filtered_entries[selected_entry_idx]
                        
                        # Display form details
                        st.markdown("### Form Details")
                        
                        # Create two columns for basic info
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown(f"**Member Name:** {selected_entry.get('member_name', '')}")
                            st.markdown(f"**Medicaid ID:** {selected_entry.get('medicaid_id', '')}")
                            st.markdown(f"**Member ID:** {selected_entry.get('member_id', '')}")
                        
                        with col2:
                            st.markdown(f"**Service Date:** {selected_entry.get('service_date', '')}")
                            st.markdown(f"**Note Category:** {selected_entry.get('note_category', '')}")
                            st.markdown(f"**Note Type:** {selected_entry.get('note_type', '')}")
                        
                        # Display TCM details if applicable
                        if selected_entry.get('note_category') == "Billable- TCM":
                            st.markdown("### TCM Details")
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown(f"**TCM Hours:** {selected_entry.get('tcm_hours', 0)}")
                                st.markdown(f"**TCM Units:** {selected_entry.get('tcm_units', 0)}")
                            
                            with col2:
                                st.markdown(f"**ICD 10:** {'Yes' if selected_entry.get('icd_10', False) else 'No'}")
                                st.markdown(f"**CPT Code:** {selected_entry.get('cpt_code', '')}")
                        
                        # Display travel details if applicable
                        if selected_entry.get('travel_to_client') == "Yes":
                            st.markdown("### Travel Details")
                            st.markdown(f"**Travel Time:** {selected_entry.get('travel_time', 0)} hours")
                            st.markdown(f"**Travel Locations:**")
                            st.text(selected_entry.get('travel_details', 'None provided'))
                        
                        # Display tasks and next steps
                        st.markdown("### Tasks and Next Steps")
                        st.markdown("**Tasks Completed:**")
                        st.text(selected_entry.get('tasks_completed', 'None provided'))
                        
                        st.markdown("**Next Steps:**")
                        st.text(selected_entry.get('next_steps', 'None provided'))
                        
                        # Display contact information if available
                        if 'first_contact' in selected_entry:
                            st.markdown("### Contact Information")
                            
                            # First contact
                            st.markdown("**First Contact:**")
                            contact = selected_entry['first_contact']
                            st.markdown(f"Name: {contact.get('contact_name', '')}")
                            st.markdown(f"Email: {contact.get('contact_email', '')}")
                            st.markdown(f"Phone: {contact.get('contact_phone', '')}")
                            st.markdown(f"Outcome: {contact.get('contact_outcome', '')}")
                            
                            # Additional contacts
                            for i, contact_key in enumerate(['second_contact', 'third_contact', 'fourth_contact']):
                                if contact_key in selected_entry:
                                    st.markdown(f"**Contact {i+2}:**")
                                    contact = selected_entry[contact_key]
                                    st.markdown(f"Name: {contact.get('contact_name', '')}")
                                    st.markdown(f"Email: {contact.get('contact_email', '')}")
                                    st.markdown(f"Phone: {contact.get('contact_phone', '')}")
                                    st.markdown(f"Outcome: {contact.get('contact_outcome', '')}")
                        
                        # Display administrative comments
                        if 'admin_comments' in selected_entry:
                            st.markdown("### Administrative Comments")
                            st.text(selected_entry.get('admin_comments', 'None provided'))
                else:
                    st.info("No entries match the selected filters.")
            else:
                st.info("No form submissions found.")
        except (FileNotFoundError, json.JSONDecodeError):
            st.info("No form submissions found.")
    
    elif st.session_state.get('admin_selection') == "Process Claims":
        st.markdown('<h2 class="subheader">Process Claims</h2>', unsafe_allow_html=True)
        
        # Load log entries
        try:
            with open('log_entries.json', 'r') as f:
                log_entries = json.load(f)
            
            # Filter for billable entries only
            billable_entries = [entry for entry in log_entries if entry.get('note_category') == "Billable- TCM"]
            
            if billable_entries:
                # Create a DataFrame for claims processing
                claims_data = []
                for entry in billable_entries:
                    claims_data.append({
                        'Medicaid ID': entry.get('medicaid_id', ''),
                        'Member Name': entry.get('member_name', ''),
                        'Service Date': entry.get('service_date', ''),
                        'TCM Hours': entry.get('tcm_hours', 0),
                        'TCM Units': entry.get('tcm_units', 0),
                        'CPT Code': entry.get('cpt_code', ''),
                        'Claim Status': 'Pending',
                        'Timestamp': entry.get('timestamp', '')
                    })
                
                df = pd.DataFrame(claims_data)
                
                # Display the claims table
                st.dataframe(df, use_container_width=True)
                
                # Add claim processing functionality
                st.markdown("### Process Selected Claims")
                
                # Allow selection of claims to process
                selected_claims = st.multiselect(
                    "Select claims to process",
                    options=range(len(billable_entries)),
                    format_func=lambda i: f"{billable_entries[i].get('member_name', '')} - {billable_entries[i].get('service_date', '')} ({billable_entries[i].get('tcm_units', 0)} units)"
                )
                
                if selected_claims:
                    # Process claims button
                    if st.button("Submit Selected Claims"):
                        st.success(f"Successfully submitted {len(selected_claims)} claims for processing.")
                        
                        # Here you would add code to update the claim status in your database
                        # For demonstration purposes, we'll just show a success message
                        
                        # You could also generate a claims report
                        st.markdown("### Claims Report")
                        
                        # Create a DataFrame with just the selected claims
                        selected_df = df.iloc[selected_claims].copy()
                        selected_df['Claim Status'] = 'Submitted'
                        
                        # Display the updated claims
                        st.dataframe(selected_df, use_container_width=True)
                        
                        # Add export functionality
                        if st.button("Export Claims Report"):
                            # Create Excel file in memory
                            output = BytesIO()
                            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                selected_df.to_excel(writer, index=False, sheet_name='Claims')
                            
                            # Set up download button
                            output.seek(0)
                            st.download_button(
                                label="Download Claims Report",
                                data=output.getvalue(),
                                file_name=f"claims_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
            else:
                st.info("No billable entries found for claims processing.")
        except (FileNotFoundError, json.JSONDecodeError):
            st.info("No form submissions found.")
    
    elif st.session_state.get('admin_selection') == "Payroll":
        st.markdown('<h2 class="subheader">Payroll Processing</h2>', unsafe_allow_html=True)
        
        # Load log entries
        try:
            with open('log_entries.json', 'r') as f:
                log_entries = json.load(f)
            
            if log_entries:
                # Create filters for payroll processing
                col1, col2 = st.columns(2)
                
                with col1:
                    # Date range filter for pay period
                    pay_period = st.date_input(
                        "Select Pay Period",
                        value=(datetime.now().date() - pd.Timedelta(days=14), datetime.now().date()),
                        max_value=datetime.now().date()
                    )
                
                with col2:
                    # Get unique TC emails from the entries
                    tc_emails = sorted(list(set(entry.get('tc_email', '') for entry in log_entries if 'tc_email' in entry)))
                    if not tc_emails:  # If no TC emails in entries, use member names as proxy
                        tc_emails = sorted(list(set(entry.get('member_name', '').split()[-1] for entry in log_entries if 'member_name' in entry)))
                    
                    selected_tc = st.selectbox("Select Transition Coordinator", ["All"] + tc_emails)
                
                # Apply filters
                filtered_entries = log_entries
                
                # Filter by date range
                if len(pay_period) == 2:
                    start_date, end_date = pay_period
                    filtered_entries = [
                        entry for entry in filtered_entries 
                        if start_date <= datetime.strptime(entry.get('service_date', '1900-01-01'), '%Y-%m-%d').date() <= end_date
                    ]
                
                # Filter by TC
                if selected_tc != "All":
                    if 'tc_email' in log_entries[0]:
                        filtered_entries = [entry for entry in filtered_entries if entry.get('tc_email') == selected_tc]
                    else:  # Use member name as proxy if tc_email not available
                        filtered_entries = [entry for entry in filtered_entries if entry.get('member_name', '').split()[-1] == selected_tc]
                
                # Create a DataFrame for payroll
                if filtered_entries:
                    payroll_data = []
                    for entry in filtered_entries:
                        # Calculate hours
                        tcm_hours = float(entry.get('tcm_hours', 0)) if 'tcm_hours' in entry else 0
                        travel_time = float(entry.get('travel_time', 0)) if 'travel_time' in entry else 0
                        total_hours = tcm_hours + travel_time
                        
                        # Calculate pay (example rate of $25/hour)
                        hourly_rate = 25.00
                        pay_amount = total_hours * hourly_rate
                        
                        payroll_data.append({
                            'TC Name': entry.get('tc_email', entry.get('member_name', '').split()[-1]),
                            'Service Date': entry.get('service_date', ''),
                            'TCM Hours': tcm_hours,
                            'Travel Hours': travel_time,
                            'Total Hours': total_hours,
                            'Pay Rate': f"${hourly_rate:.2f}",
                            'Pay Amount': f"${pay_amount:.2f}"
                        })
                    
                    df = pd.DataFrame(payroll_data)
                    
                    # Display the payroll table
                    st.dataframe(df, use_container_width=True)
                    
                    # Calculate summary statistics
                    total_tcm_hours = df['TCM Hours'].sum()
                    total_travel_hours = df['Travel Hours'].sum()
                    total_hours = df['Total Hours'].sum()
                    total_pay = sum(float(amount.replace('$', '')) for amount in df['Pay Amount'])
                    
                    # Display summary
                    st.markdown("### Payroll Summary")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Total TCM Hours", f"{total_tcm_hours:.2f}")
                    
                    with col2:
                        st.metric("Total Travel Hours", f"{total_travel_hours:.2f}")
                    
                    with col3:
                        st.metric("Total Hours", f"{total_hours:.2f}")
                    
                    with col4:
                        st.metric("Total Pay", f"${total_pay:.2f}")
                    
                    # Add export functionality
                    if st.button("Export Payroll Report"):
                        # Create Excel file in memory
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            df.to_excel(writer, index=False, sheet_name='Payroll')
                            
                            # Create a summary sheet
                            summary_df = pd.DataFrame({
                                'Metric': ['Total TCM Hours', 'Total Travel Hours', 'Total Hours', 'Total Pay'],
                                'Value': [f"{total_tcm_hours:.2f}", f"{total_travel_hours:.2f}", f"{total_hours:.2f}", f"${total_pay:.2f}"]
                            })
                            summary_df.to_excel(writer, index=False, sheet_name='Summary')
                        
                        # Set up download button
                        output.seek(0)
                        st.download_button(
                            label="Download Payroll Report",
                            data=output.getvalue(),
                            file_name=f"payroll_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                else:
                    st.info("No entries match the selected filters.")
            else:
                st.info("No form submissions found for payroll processing.")
        except (FileNotFoundError, json.JSONDecodeError):
            st.info("No form submissions found.")
    
    # If no specific admin section is selected, show dashboard
    elif not st.session_state.get('admin_selection'):
        # Create three columns for metrics
        col1, col2, col3 = st.columns(3)
        
        # Load log entries to calculate metrics
        try:
            with open('log_entries.json', 'r') as f:
                log_entries = json.load(f)
                
            # Calculate metrics
            total_forms = len(log_entries)
            
            # Count forms submitted today
            today = datetime.now().strftime("%Y-%m-%d")
            forms_today = sum(1 for entry in log_entries if entry.get('timestamp', '').startswith(today))
            
            # Count unique users (medicaid IDs)
            unique_users = len(set(entry.get('medicaid_id') for entry in log_entries if 'medicaid_id' in entry))
            
            # Display metrics
            # with col1:
            #     st.metric("Total Forms", total_forms)
            
            # with col2:
            #     st.metric("Forms Today", forms_today)
            
            # with col3:
            #     st.metric("Active Users", unique_users)
                
        except (FileNotFoundError, json.JSONDecodeError):
            # If no entries file exists or is invalid
            with col1:
                st.metric("Total Forms", 0)
            
            with col2:
                st.metric("Forms Today", 0)
            
            with col3:
                st.metric("Active Users", 0)

# Initialize session state for service date check
if 'service_date_checked' not in st.session_state:
    st.session_state.service_date_checked = False

# Initialize session state for duplicate service date confirmation
if 'duplicate_service_date_confirmed' not in st.session_state:
    st.session_state.duplicate_service_date_confirmed = False

# Main content area based on navigation
if st.session_state.nav_selection == "Member Login":
    # st.markdown('<h1 class="main-title">Member Login</h1>', unsafe_allow_html=True)
    
    # Only show login form if not already verified
    if not st.session_state.member_verified:
        # Center the login form
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            # Load the dataframe to get TC email and Medicaid IDs
            try:
                df = pd.read_excel('./Master_db.xlsx')
                
                # Get unique TC emails for username dropdown
                tc_emails = df['TC EMAIL'].dropna().unique().tolist()
                
                # Create a selectbox for username outside the form
                username = st.selectbox("Username (TC Email)", tc_emails)
                
                # Filter Medicaid IDs based on selected TC email
                if username:
                    filtered_df = df[df['TC EMAIL'] == username]
                    medicaid_ids = filtered_df['MedicaidID'].dropna().unique().tolist()
                
                # Now create the login form with the filtered Medicaid IDs
                with st.form("member_login"):
                    selected_medicaid_id = st.selectbox("Select Medicaid ID", medicaid_ids if username else [])
                    
                    # Get the TC name for password verification
                    if username and selected_medicaid_id is not None:
                        tc_row = filtered_df[filtered_df['MedicaidID'] == selected_medicaid_id].iloc[0]
                        expected_password = tc_row.get('TRANSITION COORDINATOR', '')
                    else:
                        expected_password = ""
                    
                    password = st.text_input("Password", type="password")
                    submit = st.form_submit_button("Login")
                    
                    if submit:
                        try:
                            # Validate Medicaid ID format
                            is_valid, error_msg = validate_medicaid_id(selected_medicaid_id)
                            if not is_valid:
                                st.error(error_msg)
                            else:
                                # Check if the password matches the TC name
                                if password == expected_password:
                                    # Get member details from the dataframe
                                    member_details = {
                                        'medicaid_id': selected_medicaid_id,
                                        'member_name': f"{tc_row.get('FIRST NAME', '')} {tc_row.get('LAST NAME', '')}",
                                        'member_id': tc_row.get('MEMBER ID', ''),
                                        'member_dob': tc_row.get('DOB', '')
                                    }
                                    
                                    st.session_state.member_verified = True
                                    st.session_state.member_data = member_details
                                    
                                    # Initialize form section if not already set
                                    if 'current_section' not in st.session_state:
                                        st.session_state.current_section = 1
                                    
                                    # Success message
                                    st.success("Login successful!")
                                    
                                    # Reset service date check flag
                                    st.session_state.service_date_checked = False
                                    st.session_state.duplicate_service_date_confirmed = False
                                    
                                    # Automatically redirect to form page
                                    st.session_state.nav_selection = "Form"
                                    st.rerun()
                                else:
                                    st.error("Invalid password. Please try again.")
                        except Exception as e:
                            st.error(f"Error during login: {str(e)}")
                            print(f"Error during login: {str(e)}")  # Debug log
            except Exception as e:
                st.error(f"Error loading member data: {str(e)}")
                print(f"Error loading member data: {str(e)}")  # Debug log
                
                # Fallback to original login form if data loading fails
                with st.form("member_login_fallback"):
                    username = st.text_input("Username (Medicaid ID)")
                    password = st.text_input("Password", type="password")
                    submit = st.form_submit_button("Login")
                    
                    if submit:
                        try:
                            # Validate Medicaid ID format
                            is_valid, error_msg = validate_medicaid_id(username)
                            if not is_valid:
                                st.error(error_msg)
                            else:
                                # Check if the Medicaid ID exists in the database
                                member_details = get_member_details(username)
                                
                                if not member_details:
                                    st.error("Invalid Medicaid ID. Please try again.")
                                else:
                                    # For demo purposes, accept any password
                                    st.session_state.member_verified = True
                                    st.session_state.member_data = member_details
                                    
                                    # Initialize form section if not already set
                                    if 'current_section' not in st.session_state:
                                        st.session_state.current_section = 1
                                    
                                    # Success message
                                    st.success("Login successful!")
                                    
                                    # Reset service date check flag
                                    st.session_state.service_date_checked = False
                                    st.session_state.duplicate_service_date_confirmed = False
                                    
                                    # Automatically redirect to form page
                                    st.session_state.nav_selection = "Form"
                                    st.rerun()
                        except Exception as e:
                            st.error(f"Error during login: {str(e)}")
                            print(f"Error during login: {str(e)}")  # Debug log
    else:
        # If already verified, redirect to form page
        st.session_state.nav_selection = "Form"
        st.rerun()

# Create a new navigation option for the form
elif st.session_state.nav_selection == "Form":
    # Only allow access if member is verified
    if not st.session_state.member_verified:
        st.warning("Please login first to access the form.")
        st.session_state.nav_selection = "Member Login"
        st.rerun()
    
    # Display member info at the top
    member_info_col1, member_info_col2 = st.columns(2)
    with member_info_col1:
        st.markdown(f"**Member:** {st.session_state.member_data.get('member_name', '')}")
        st.markdown(f"**Medicaid ID:** {st.session_state.member_data.get('medicaid_id', '')}")
    with member_info_col2:
        st.markdown(f"**Member ID:** {st.session_state.member_data.get('member_id', '')}")
        if 'member_dob' in st.session_state.member_data:
            try:
                dob = pd.to_datetime(st.session_state.member_data['member_dob']).strftime('%Y-%m-%d')
                st.markdown(f"**DOB:** {dob}")
            except:
                pass
    
    st.markdown("---")
    
    # Check for existing records with the same service date
    if not st.session_state.service_date_checked:
        with st.form("service_date_form"):
            service_date = st.date_input("Please enter the service date for this form")
            submit_date = st.form_submit_button("Continue")
            
            if submit_date:
                # Check if there are existing records with the same service date and medicaid ID
                try:
                    with open('log_entries.json', 'r') as f:
                        all_entries = json.load(f)
                    
                    # Convert service_date to string for comparison
                    service_date_str = service_date.strftime("%Y-%m-%d")
                    medicaid_id = st.session_state.member_data.get('medicaid_id', '')
                    
                    # Find entries with matching service date and medicaid ID
                    matching_entries = [
                        entry for entry in all_entries 
                        if entry.get('service_date') == service_date_str and 
                           entry.get('medicaid_id') == medicaid_id
                    ]
                    
                    if matching_entries:
                        # Store the service date in session state
                        st.session_state.selected_service_date = service_date
                        st.session_state.service_date_checked = True
                        st.rerun()  # Rerun to show confirmation dialog
                    else:
                        # No matching entries, proceed with form
                        st.session_state.service_date_checked = True
                        st.session_state.duplicate_service_date_confirmed = True
                        # Store the service date for later use
                        st.session_state.selected_service_date = service_date
                        st.rerun()
                except (FileNotFoundError, json.JSONDecodeError):
                    # No existing entries file or invalid JSON
                    st.session_state.service_date_checked = True
                    st.session_state.duplicate_service_date_confirmed = True
                    # Store the service date for later use
                    st.session_state.selected_service_date = service_date
                    st.rerun()
    
    # Show confirmation dialog if duplicate service date found and not yet confirmed
    elif st.session_state.service_date_checked and not st.session_state.duplicate_service_date_confirmed:
        st.warning(f"There are already entries for {st.session_state.selected_service_date.strftime('%Y-%m-%d')} for this member. Do you want to continue?")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, continue with this date"):
                st.session_state.duplicate_service_date_confirmed = True
                st.rerun()
        with col2:
            if st.button("No, choose a different date"):
                st.session_state.service_date_checked = False
                st.rerun()
    
    # Only show progress bar for non-Administrative notes
    elif st.session_state.duplicate_service_date_confirmed:
        # Create the progress steps
        def create_progress_bar(current_section, total_sections):
            html = '<div class="step-container">'
            for i in range(1, total_sections + 1):
                if i < current_section:
                    html += f'<div class="step completed">{i}</div>'
                elif i == current_section:
                    html += f'<div class="step active">{i}</div>'
                else:
                    html += f'<div class="step">{i}</div>'
                
                if i < total_sections:
                    if i < current_section:
                        html += '<div class="step-line completed"></div>'
                    else:
                        html += '<div class="step-line"></div>'
            html += '</div>'
            return html

        # Only show progress bar for non-Administrative notes
        if st.session_state.get('form_data', {}).get('note_category') != "Administrative":
            # Progress bar with custom styling
            st.markdown(create_progress_bar(st.session_state.current_section, TOTAL_SECTIONS), unsafe_allow_html=True)
            st.markdown(f'<p class="progress-text">Section {st.session_state.current_section} of {TOTAL_SECTIONS}</p>', unsafe_allow_html=True)
        
        # Before the form, check if we need to set a note category
        if 'note_category' not in st.session_state:
            st.session_state.note_category = "Billable- TCM"  # Default value
        
        # Only show note type selection in section 1
        if st.session_state.current_section == 1:
            # Create a container outside the form to handle note type selection
            note_type_container = st.container()
            with note_type_container:
                # Note type selection outside the form
                temp_note_category = st.radio(
                    "Type of Note", 
                    ["Administrative", "Billable- TCM"],
                    index=0 if st.session_state.note_category == "Administrative" else 1,
                    key="note_category_selector",  # Use a different key
                    horizontal=True  # Display options horizontally
                )
                
                # Update session state when selection changes
                if temp_note_category != st.session_state.note_category:
                    st.session_state.note_category = temp_note_category
                    # Reset form data when changing note type
                    if 'form_data' in st.session_state:
                        st.session_state.form_data = {}
                    st.rerun()
            
            # Inside the forms
            if st.session_state.note_category == "Administrative":
                # Administrative form
                with st.form("admin_form"):
                    st.markdown('<h2 class="subheader">DEMOGRAPHICS</h2>', unsafe_allow_html=True)
                    
                    # Get medicaid_id from session state
                    medicaid_id = st.session_state.member_data.get('medicaid_id', '')
                    
                    # Get member details if available
                    member_details = st.session_state.member_data
                    
                    medicaid_id_display = st.text_input(
                        "MEDICAID ID *",
                        value=medicaid_id,
                        disabled=True,  # Make non-editable
                        key="medicaid_id_display"
                    )
                    
                    member_name = st.text_input(
                        "MEMBER NAME *",
                        value=member_details.get('member_name', ''),
                        disabled=True,
                        key="member_name"
                    )
                    
                    # Handle DOB properly
                    try:
                        if 'member_dob' in member_details and member_details['member_dob']:
                            # Try to convert to datetime first
                            if isinstance(member_details['member_dob'], (str, datetime, date)):
                                dob_value = pd.to_datetime(member_details['member_dob']).date()
                            else:
                                # If it's a float or other type, convert to string first
                                dob_str = str(member_details['member_dob'])
                                if dob_str and dob_str.lower() != 'nan':
                                    dob_value = pd.to_datetime(dob_str).date()
                                else:
                                    dob_value = datetime.now().date()
                        else:
                            dob_value = datetime.now().date()
                        
                        member_dob = st.date_input(
                            "MEMBER DOB *",
                            value=dob_value,
                            disabled=True,
                            key="member_dob"
                        )
                    except Exception as e:
                        st.error(f"Error processing date of birth: {str(e)}")
                        # Fallback to current date
                        member_dob = st.date_input(
                            "MEMBER DOB *",
                            value=datetime.now().date(),
                            disabled=True,
                            key="member_dob"
                        )

                    st.markdown('<p class="section-number">1.1)</p>', unsafe_allow_html=True)
                    # Make Member ID non-editable
                    member_id = st.text_input(
                        "MEMBER ID", 
                        value=str(member_details.get('member_id', '')),  # Convert to string
                        disabled=True,
                        key="member_id", 
                        help="Member ID must be a numerical value"
                    )
                    
                    st.markdown('<p class="section-number">1.2)</p>', unsafe_allow_html=True)
                    note_type = st.radio(
                        "Is this a new note or an amendment to correct a previous note?",
                        ["New Note", "Amendment"]
                    )
                    
                    # Always show the amendment reason field
                    st.markdown('<p class="section-number">1.2a)</p>', unsafe_allow_html=True)
                    amendment_reason = st.text_area(
                        "REASON FOR FORM AMENDMENT",
                        height=100,
                        key="amendment_reason"
                    )
                    
                    st.markdown('<p class="section-number">1.3)</p>', unsafe_allow_html=True)
                    # Use the selected service date from earlier
                    service_date = st.date_input(
                        "DATE OF SERVICE", 
                        value=st.session_state.selected_service_date,
                        disabled=True
                    )
                    
                    st.markdown('<p class="section-number">1.4)</p>', unsafe_allow_html=True)
                    travel_to_client = st.radio("Did you travel to/for client", ["Yes", "No"])
                    
                    if travel_to_client == "Yes":
                        st.markdown('<p class="section-number">1.4a)</p>', unsafe_allow_html=True)
                        col1, col2 = st.columns(2)
                        with col1:
                            travel_time = st.number_input(
                                "TOTAL CLIENT TRAVEL TIME (15 min increments)",
                                min_value=0.0,
                                max_value=24.0,
                                step=0.25
                            )
                        with col2:
                            st.markdown("""
                            **Decimal Conversion:**
                            - 15 minutes = 0.25
                            - 30 minutes = 0.50
                            - 45 minutes = 0.75
                            - 60 minutes = 1.00
                            """)
                        
                        st.markdown('<p class="section-number">1.4b)</p>', unsafe_allow_html=True)
                        st.markdown("""
                        In this section, please specify the details of all your travel destinations, 
                        including the starting and ending addresses for each stop.
                        """)
                        travel_details = st.text_area("OUTLINE EACH DESTINATION TO AND FROM LOCATIONS")
                    
                    # Hidden field to store the note category - use a different key
                    st.markdown('<p class="section-number">1.5)</p>', unsafe_allow_html=True)

                    st.text_input("Note Category", value=st.session_state.note_category, 
                                 key="note_category_hidden_admin", label_visibility="hidden", disabled=True)
                    
                    st.markdown('<p class="section-number">1.5a)</p>', unsafe_allow_html=True)
                    st.markdown("**Administrative Type**")
                    admin_type = st.radio(
                        "Select Administrative Type",
                        options=["MEETING", "Training", "Travel"],
                        key="admin_type_radio",
                        label_visibility="collapsed"
                    )
                    
                    # For Administrative notes, show section 8.1 directly here
                    # st.markdown('<p class="section-number">8.1)</p>', unsafe_allow_html=True)
                    st.markdown("**PLEASE ENTER ADMINISTRATIVE WORK COMPLETED**")
                    admin_comments = st.text_area(
                        "Enter administrative work details",
                        height=200,
                        help="Provide details about the administrative work completed",
                        key="admin_comments_direct"
                    )
                    
                    # Hidden fields for required database fields
                    total_travel_time_hidden = 0.0
                    travel_locations_hidden = ""
                    travel_comments_hidden = ""
                    tasks_completed_hidden = "Administrative task"
                    next_steps_hidden = "N/A for Administrative note"
                    contact_types_hidden = ["DOCUMENTATION"]
                    
                    # Add a submit button at the bottom of the form
                    admin_submitted = st.form_submit_button("Submit")
                    
                    if admin_submitted:
                        # Process Administrative form submission
                        # REMOVE ANY VALIDATION CODE FOR MEMBER ID
                        
                        # Save the form data
                        form_data = {
                            'medicaid_id': medicaid_id,
                            'member_name': member_name,
                            'member_id': member_id,  # Use as-is without validation
                            'member_dob': member_dob,
                            'note_type': note_type,
                            'service_date': service_date,
                            'travel_to_client': travel_to_client,
                            'note_category': st.session_state.note_category
                        }
                        
                        # Add amendment reason if applicable
                        if note_type == "Amendment" and 'amendment_reason' in locals():
                            form_data['amendment_reason'] = amendment_reason
                        
                        # Add travel details if applicable
                        if travel_to_client == "Yes":
                            form_data['travel_time'] = travel_time
                            form_data['travel_details'] = travel_details
                        
                        # Add admin type if applicable
                        form_data['admin_type'] = admin_type
                        form_data['admin_comments'] = admin_comments
                        
                        # Add default values for required fields in other sections
                        form_data['total_travel_time'] = total_travel_time_hidden
                        form_data['travel_locations'] = travel_locations_hidden
                        form_data['travel_comments'] = travel_comments_hidden
                        form_data['tasks_completed'] = tasks_completed_hidden
                        form_data['next_steps'] = next_steps_hidden
                        form_data['contact_types'] = contact_types_hidden
                        
                        # For Administrative notes, create the complete entry and submit
                        entry = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            **form_data
                        }
                        
                        st.session_state.log_entries.append(entry)
                        save_entries()
                        st.session_state.form_data = {}
                        st.success("Administrative form submitted successfully!")
                        
                        # Reset form-related session states
                        st.session_state.current_section = 1
                        st.session_state.member_verified = False
                        st.session_state.member_data = {}
                        
                        # Change navigation to Member Login
                        st.session_state.nav_selection = "Member Login"
                        st.rerun()
            else:  # Billable- TCM form
                with st.form("tcm_form_section1"):
                    st.markdown('<h2 class="subheader">DEMOGRAPHICS</h2>', unsafe_allow_html=True)
                    
                    # Get medicaid_id from session state
                    medicaid_id = st.session_state.member_data.get('medicaid_id', '')
                    
                    # Get member details if available
                    member_details = st.session_state.member_data
                    
                    medicaid_id_display = st.text_input(
                        "MEDICAID ID *",
                        value=medicaid_id,
                        disabled=True,  # Make non-editable
                        key="medicaid_id_display"
                    )
                    
                    member_name = st.text_input(
                        "MEMBER NAME *",
                        value=member_details.get('member_name', ''),
                        disabled=True,
                        key="member_name"
                    )
                    
                    # Handle DOB properly
                    try:
                        if 'member_dob' in member_details and member_details['member_dob']:
                            # Try to convert to datetime first
                            if isinstance(member_details['member_dob'], (str, datetime, date)):
                                dob_value = pd.to_datetime(member_details['member_dob']).date()
                            else:
                                # If it's a float or other type, convert to string first
                                dob_str = str(member_details['member_dob'])
                                if dob_str and dob_str.lower() != 'nan':
                                    dob_value = pd.to_datetime(dob_str).date()
                                else:
                                    dob_value = datetime.now().date()
                        else:
                            dob_value = datetime.now().date()
                        
                        member_dob = st.date_input(
                            "MEMBER DOB *",
                            value=dob_value,
                            disabled=True,
                            key="member_dob"
                        )
                    except Exception as e:
                        st.error(f"Error processing date of birth: {str(e)}")
                        # Fallback to current date
                        member_dob = st.date_input(
                            "MEMBER DOB *",
                            value=datetime.now().date(),
                            disabled=True,
                            key="member_dob"
                        )

                    st.markdown('<p class="section-number">1.1)</p>', unsafe_allow_html=True)
                    # Make Member ID non-editable
                    member_id = st.text_input(
                        "MEMBER ID", 
                        value=str(member_details.get('member_id', '')),  # Convert to string
                        disabled=True,
                        key="member_id", 
                        help="Member ID must be a numerical value"
                    )
                    
                    st.markdown('<p class="section-number">1.2)</p>', unsafe_allow_html=True)
                    note_type = st.radio(
                        "Is this a new note or an amendment to correct a previous note?",
                        ["New Note", "Amendment"]
                    )
                    
                    # Always show the amendment reason field
                    st.markdown('<p class="section-number">1.2a)</p>', unsafe_allow_html=True)
                    amendment_reason = st.text_area(
                        "REASON FOR FORM AMENDMENT",
                        height=100,
                        key="amendment_reason"
                    )
                    
                    st.markdown('<p class="section-number">1.3)</p>', unsafe_allow_html=True)
                    # Use the selected service date from earlier
                    service_date = st.date_input(
                        "DATE OF SERVICE", 
                        value=st.session_state.selected_service_date,
                        disabled=True
                    )
                    
                    st.markdown('<p class="section-number">1.4)</p>', unsafe_allow_html=True)
                    travel_to_client = st.radio("Did you travel to/for client", ["Yes", "No"])
                    
                    if travel_to_client == "Yes":
                        st.markdown('<p class="section-number">1.4a)</p>', unsafe_allow_html=True)
                        col1, col2 = st.columns(2)
                        with col1:
                            travel_time = st.number_input(
                                "TOTAL CLIENT TRAVEL TIME (15 min increments)",
                                min_value=0.0,
                                max_value=24.0,
                                step=0.25
                            )
                        with col2:
                            st.markdown("""
                            **Decimal Conversion:**
                            - 15 minutes = 0.25
                            - 30 minutes = 0.50
                            - 45 minutes = 0.75
                            - 60 minutes = 1.00
                            """)
                        
                        st.markdown('<p class="section-number">1.4b)</p>', unsafe_allow_html=True)
                        st.markdown("""
                        In this section, please specify the details of all your travel destinations, 
                        including the starting and ending addresses for each stop.
                        """)
                        travel_details = st.text_area("OUTLINE EACH DESTINATION TO AND FROM LOCATIONS")
                    
                    # Hidden field to store the note category - use a different key
                    st.markdown('<p class="section-number">1.5)</p>', unsafe_allow_html=True)

                    st.text_input("Note Category", value=st.session_state.note_category, 
                                 key="note_category_hidden_tcm", label_visibility="hidden", disabled=True)
                    
                    # TCM-specific fields
                    st.markdown('<p class="section-number">1.6)</p>', unsafe_allow_html=True)
                    col1, col2 = st.columns(2)
                    with col1:
                        tcm_hours = st.number_input(
                            "TCM HOURS (15 min increments)",
                            min_value=0.0,
                            max_value=24.0,
                            step=0.25
                        )
                    with col2:
                        st.markdown("""
                        **Decimal Conversion:**
                        - 15 minutes = 0.25
                        - 30 minutes = 0.50
                        - 45 minutes = 0.75
                        - 60 minutes = 1.00
                        """)
                    
                    st.markdown('<p class="section-number">1.7)</p>', unsafe_allow_html=True)
                    col1, col2 = st.columns(2)
                    with col1:
                        tcm_units = st.number_input(
                            "TCM UNITS",
                            min_value=0,
                            max_value=96,
                            step=1
                        )
                    with col2:
                        st.markdown("""
                        **Unit Conversion:**
                        - 15 minutes = 1 unit
                        - 30 minutes = 2 units
                        - 45 minutes = 3 units
                        - 60 minutes = 4 units
                        """)
                    
                    st.markdown('<p class="section-number">1.8)</p>', unsafe_allow_html=True)
                    icd_10 = st.checkbox("ICD 10 - R99", 
                                        help="International Classification of Diseases, 10th revision code")

                    st.markdown('<p class="section-number">1.9)</p>', unsafe_allow_html=True)
                    cpt_code = st.selectbox(
                        "CPT CODE",
                        ["Please select",
                        "T1017 TRANSITION COORDINATION",
                         "T2038 HOUSEHOLD SET UP TIME",
                         "Administrative"]
                    )
                    
                    # Add a Next button at the bottom of the form
                    tcm_submitted = st.form_submit_button("Next")
                    
                    if tcm_submitted:
                        # Process TCM form section 1 submission
                        # REMOVE ANY VALIDATION CODE FOR MEMBER ID
                        
                        # Save the form data
                        form_data = {
                            'medicaid_id': medicaid_id,
                            'member_name': member_name,
                            'member_id': member_id,  # Use as-is without validation
                            'member_dob': member_dob,
                            'note_type': note_type,
                            'service_date': service_date,
                            'travel_to_client': travel_to_client,
                            'note_category': st.session_state.note_category
                        }
                        
                        # Add amendment reason if applicable
                        if note_type == "Amendment" and 'amendment_reason' in locals():
                            form_data['amendment_reason'] = amendment_reason
                        
                        # Add travel details if applicable
                        if travel_to_client == "Yes":
                            form_data['travel_time'] = travel_time
                            form_data['travel_details'] = travel_details
                        
                        # Add TCM details
                        form_data['tcm_hours'] = tcm_hours
                        form_data['tcm_units'] = tcm_units
                        form_data['icd_10'] = icd_10
                        form_data['cpt_code'] = cpt_code
                        
                        # Update session state and proceed to next section
                        st.session_state.form_data = form_data  # Replace with new data
                        st.session_state.current_section = 2
                        st.rerun()

    # For section 2 and beyond, don't show the note type selection
    elif st.session_state.current_section > 1:
        # Section 2 (Travel Form)
        if st.session_state.current_section == 2:
            with st.form("travel_form"):
                st.markdown('<h2 class="subheader">ADMINISTRATIVE TRAVEL DETAILS</h2>', unsafe_allow_html=True)
                
                st.markdown('<p class="section-number">2.1)</p>', unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    total_travel_time = st.number_input(
                        "TOTAL TRAVEL TIME (15 min increments)",
                        min_value=0.0,
                        max_value=24.0,
                        step=0.25
                    )
                with col2:
                    st.markdown("""
                    **Decimal Conversion:**
                    - 15 minutes = 0.25
                    - 30 minutes = 0.50
                    - 45 minutes = 0.75
                    - 60 minutes = 1.00
                    """)
                
                st.markdown('<p class="section-number">2.2)</p>', unsafe_allow_html=True)
                st.markdown("**OUTLINE EACH DESTINATION TO AND FROM LOCATIONS**")
                travel_locations = st.text_area(
                    "Enter travel details",
                    height=150,
                    help="Please specify all locations visited in chronological order"
                )
                
                st.markdown('<p class="section-number">2.3)</p>', unsafe_allow_html=True)
                st.markdown("**ADDITIONAL COMMENTS**")
                travel_comments = st.text_area(
                    "Enter any additional comments",
                    height=100,
                    help="Add any relevant notes about the travel or visits"
                )

                submitted = st.form_submit_button("Next")
                if submitted:
                    # Save section 2 data
                    section_data = {
                        'total_travel_time': total_travel_time,
                        'travel_locations': travel_locations,
                        'travel_comments': travel_comments
                    }
                    
                    # Update session state
                    st.session_state.form_data.update(section_data)
                    
                    # Move to next section
                    st.session_state.current_section += 1
                    st.rerun()

        # Section 3 (Tasks Completed)
        elif st.session_state.current_section == 3:
            with st.form("tasks_form"):
                st.markdown('<h2 class="subheader">TASKS COMPLETED</h2>', unsafe_allow_html=True)
                
                st.markdown("**TRANSITION COORDINATION TASK COMPLETED**")
                tasks_completed_text = st.text_area(
                    "Enter tasks completed",
                    height=150,
                    help="Describe all transition coordination tasks completed during this session"
                )
                
                st.markdown("**NEXT STEPS/PLAN FOR FOLLOW UP**")
                next_steps = st.text_area(
                    "Enter next steps and follow-up plan",
                    height=150,
                    help="Detail the planned next steps and follow-up actions"
                )
                
                st.markdown("**TYPE OF CONTACT**")
                contact_types = st.multiselect(
                    "Select type(s) of contact",
                    options=[
                        "CALL",
                        "EMAIL",
                        "IN PERSON",
                        "DOCUMENTATION",
                        "Other"
                    ]
                )
                
                # Initialize other_contact_type as None
                other_contact_type = None
                
                # If Other is selected, show text field for specification
                if "Other" in contact_types:
                    other_contact_type = st.text_input(
                        "Please specify other contact type(s)",
                        help="Enter the specific type(s) of contact used"
                    )

                submitted = st.form_submit_button("Next")
                if submitted:
                    # Save section 3 data
                    section_data = {
                        'tasks_completed': tasks_completed_text,
                        'next_steps': next_steps,
                        'contact_types': contact_types,
                    }
                    
                    # Only add other_contact_type if it exists
                    if other_contact_type:
                        section_data['other_contact_type'] = other_contact_type
                    
                    # Update session state
                    st.session_state.form_data.update(section_data)
                    
                    # Move to next section
                    st.session_state.current_section += 1
                    st.rerun()

        # Section 4 (First Contact)
        elif st.session_state.current_section == 4:
            st.markdown('<h2 class="subheader">FIRST CONTACT</h2>', unsafe_allow_html=True)
            
            with st.form("first_contact_form"):  # Wrap in form
                st.markdown('<p class="section-number">4.1)</p>', unsafe_allow_html=True)
                first_contact_name = st.text_input("FULL NAME")
                
                st.markdown('<p class="section-number">4.2)</p>', unsafe_allow_html=True)
                first_contact_email = st.text_input("EMAIL")
                
                st.markdown('<p class="section-number">4.3)</p>', unsafe_allow_html=True)
                first_contact_phone = st.text_input(
                    "PHONE NUMBER",
                    help="Format: +1 XXX-XXX-XXXX (must include +1)",
                    placeholder="+1 XXX-XXX-XXXX"
                )
                
                st.markdown('<p class="section-number">4.4)</p>', unsafe_allow_html=True)
                first_contact_outcome = st.radio(
                    "OUTCOME",
                    options=[
                        "DISCONNECTED/WRONG NUMBER",
                        "EMAIL",
                        "LEFT MESSAGE",
                        "NO ANSWER",
                        "SPOKE TO CONTACT",
                        "VOICEMAIL FULL",
                        "Other"
                    ]
                )
                
                first_contact_other_outcome = None
                if first_contact_outcome == "Other":
                    first_contact_other_outcome = st.text_input("Please specify other outcome")
                
                st.markdown('<p class="section-number">4.5)</p>', unsafe_allow_html=True)
                need_second_contact = st.radio(
                    "Do you have another contact to enter?",
                    ["Yes", "No"]
                )
                
                # Add the Next button inside the form
                submitted = st.form_submit_button("Next")
                if submitted:
                    # Save the contact information to session state
                    contact_data = {
                        'contact_name': first_contact_name,
                        'contact_email': first_contact_email,
                        'contact_phone': first_contact_phone,
                        'contact_outcome': first_contact_outcome
                    }
                    if first_contact_outcome == "Other" and first_contact_other_outcome:
                        contact_data['other_outcome'] = first_contact_other_outcome
                    
                    st.session_state.form_data.update({'first_contact': contact_data})
                    
                    # Determine next section based on need_second_contact
                    if need_second_contact == "Yes":
                        st.session_state.current_section = 5  # Go to second contact
                    else:
                        st.session_state.current_section = 8  # Skip to final section
                    st.rerun()

        # Section 5 (Second Contact)
        elif st.session_state.current_section == 5:
            st.markdown('<h2 class="subheader">SECOND CONTACT</h2>', unsafe_allow_html=True)
            
            with st.form("second_contact_form_section5"):
                st.markdown('<p class="section-number">5.1)</p>', unsafe_allow_html=True)
                second_contact_name = st.text_input("FULL NAME", key="second_contact_name_sec5")
                
                st.markdown('<p class="section-number">5.2)</p>', unsafe_allow_html=True)
                second_contact_email = st.text_input("EMAIL", key="second_contact_email_sec5")
                
                st.markdown('<p class="section-number">5.3)</p>', unsafe_allow_html=True)
                second_contact_phone = st.text_input(
                    "PHONE NUMBER",
                    help="Format: +1 XXX-XXX-XXXX (must include +1)",
                    placeholder="+1 XXX-XXX-XXXX",
                    key="second_contact_phone_sec5"
                )
                
                st.markdown('<p class="section-number">5.4)</p>', unsafe_allow_html=True)
                second_contact_outcome = st.radio(
                    "OUTCOME",
                    options=[
                        "SPOKE TO CONTACT",
                        "LEFT MESSAGE",
                        "DISCONNECTED/WRONG NUMBER",
                        "NO ANSWER",
                        "VOICEMAIL FULL",
                        "Other"
                    ],
                    key="second_contact_outcome_sec5"
                )
                
                second_contact_other_outcome = None
                if second_contact_outcome == "Other":
                    second_contact_other_outcome = st.text_input(
                        "Please specify other outcome (Second Contact)",
                        key="second_contact_other_outcome_sec5"
                    )
                
                st.markdown('<p class="section-number">5.5)</p>', unsafe_allow_html=True)
                need_third_contact = st.radio(
                    "Do you need to enter another contact?",
                    ["Yes", "No"],
                    key="need_third_contact_sec5"
                )
                
                submitted = st.form_submit_button("Next")
                if submitted:
                    # Save contact information
                    contact_data = {
                        'contact_name': second_contact_name,
                        'contact_email': second_contact_email,
                        'contact_phone': second_contact_phone,
                        'contact_outcome': second_contact_outcome
                    }
                    if second_contact_outcome == "Other" and second_contact_other_outcome:
                        contact_data['other_outcome'] = second_contact_other_outcome
                    
                    st.session_state.form_data.update({'second_contact': contact_data})
                    
                    # Navigate based on need_third_contact
                    if need_third_contact == "Yes":
                        st.session_state.current_section = 6
                    else:
                        st.session_state.current_section = 8
                    st.rerun()

        # Section 6 (Third Contact)
        elif st.session_state.current_section == 6:
            st.markdown('<h2 class="subheader">THIRD CONTACT</h2>', unsafe_allow_html=True)
            
            with st.form("third_contact_form_section6"):
                st.markdown('<p class="section-number">6.1)</p>', unsafe_allow_html=True)
                third_contact_name = st.text_input("FULL NAME", key="third_contact_name_sec6")
                
                st.markdown('<p class="section-number">6.2)</p>', unsafe_allow_html=True)
                third_contact_email = st.text_input("EMAIL", key="third_contact_email_sec6")
                
                st.markdown('<p class="section-number">6.3)</p>', unsafe_allow_html=True)
                third_contact_phone = st.text_input(
                    "PHONE NUMBER",
                    help="Format: +1 XXX-XXX-XXXX (must include +1)",
                    placeholder="+1 XXX-XXX-XXXX",
                    key="third_contact_phone_sec6"
                )
                
                st.markdown('<p class="section-number">6.4)</p>', unsafe_allow_html=True)
                third_contact_outcome = st.radio(
                    "OUTCOME",
                    options=[
                        "SPOKE TO CONTACT",
                        "LEFT MESSAGE",
                        "DISCONNECTED/WRONG NUMBER",
                        "NO ANSWER",
                        "VOICEMAIL FULL",
                        "Other"
                    ],
                    key="third_contact_outcome_sec6"
                )
                
                third_contact_other_outcome = None
                if third_contact_outcome == "Other":
                    third_contact_other_outcome = st.text_input(
                        "Please specify other outcome (Third Contact)",
                        key="third_contact_other_outcome_sec6"
                    )
                
                st.markdown('<p class="section-number">6.5)</p>', unsafe_allow_html=True)
                need_fourth_contact = st.radio(
                    "Do you need to enter another contact?",
                    ["Yes", "No"],
                    key="need_fourth_contact_sec6"
                )
                
                submitted = st.form_submit_button("Next")
                if submitted:
                    # Save contact information
                    contact_data = {
                        'contact_name': third_contact_name,
                        'contact_email': third_contact_email,
                        'contact_phone': third_contact_phone,
                        'contact_outcome': third_contact_outcome
                    }
                    if third_contact_outcome == "Other" and third_contact_other_outcome:
                        contact_data['other_outcome'] = third_contact_other_outcome
                    
                    st.session_state.form_data.update({'third_contact': contact_data})
                    
                    # Navigate based on need_fourth_contact
                    if need_fourth_contact == "Yes":
                        st.session_state.current_section = 7
                    else:
                        st.session_state.current_section = 8
                    st.rerun()

        # Section 7 (Fourth Contact)
        elif st.session_state.current_section == 7:
            st.markdown('<h2 class="subheader">FOURTH CONTACT</h2>', unsafe_allow_html=True)
            
            with st.form("fourth_contact_form_section7"):
                st.markdown('<p class="section-number">7.1)</p>', unsafe_allow_html=True)
                fourth_contact_name = st.text_input("FULL NAME", key="fourth_contact_name_sec7")
                
                st.markdown('<p class="section-number">7.2)</p>', unsafe_allow_html=True)
                fourth_contact_email = st.text_input("EMAIL", key="fourth_contact_email_sec7")
                
                st.markdown('<p class="section-number">7.3)</p>', unsafe_allow_html=True)
                fourth_contact_phone = st.text_input(
                    "PHONE NUMBER",
                    help="Format: +1 XXX-XXX-XXXX (must include +1)",
                    placeholder="+1 XXX-XXX-XXXX",
                    key="fourth_contact_phone_sec7"
                )
                
                st.markdown('<p class="section-number">7.4)</p>', unsafe_allow_html=True)
                fourth_contact_outcome = st.radio(
                    "OUTCOME",
                    options=[
                        "SPOKE TO CONTACT",
                        "LEFT MESSAGE",
                        "DISCONNECTED/WRONG NUMBER",
                        "NO ANSWER",
                        "VOICEMAIL FULL",
                        "Other"
                    ],
                    key="fourth_contact_outcome_sec7"
                )
                
                fourth_contact_other_outcome = None
                if fourth_contact_outcome == "Other":
                    fourth_contact_other_outcome = st.text_input(
                        "Please specify other outcome (Fourth Contact)",
                        key="fourth_contact_other_outcome_sec7"
                    )
                
                submitted = st.form_submit_button("Next")
                if submitted:
                    # Save contact information
                    contact_data = {
                        'contact_name': fourth_contact_name,
                        'contact_email': fourth_contact_email,
                        'contact_phone': fourth_contact_phone,
                        'contact_outcome': fourth_contact_outcome
                    }
                    if fourth_contact_outcome == "Other" and fourth_contact_other_outcome:
                        contact_data['other_outcome'] = fourth_contact_other_outcome
                    
                    st.session_state.form_data.update({'fourth_contact': contact_data})
                    
                    # Move to final section
                    st.session_state.current_section = 8
                    st.rerun()

        # Section 8 (Final Section)
        elif st.session_state.current_section == 8:
            st.markdown('<h2 class="subheader">ADMINISTRATIVE COMMENTS</h2>', unsafe_allow_html=True)
            
            with st.form("final_form_section8"):
                st.markdown('<p class="section-number">8.1)</p>', unsafe_allow_html=True)
                st.markdown("**PLEASE ENTER ADMINISTRATIVE WORK COMPLETED**")
                admin_comments = st.text_area(
                    "Enter administrative work details",
                    height=200,
                    help="Provide details about the administrative work completed",
                    key="admin_comments_sec8"
                )
                
                submitted = st.form_submit_button("Submit")
                if submitted:
                    # Handle final submission
                    # Create the entry with all fields as they are
                    entry = {
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        **st.session_state.form_data,
                        "admin_comments": admin_comments if admin_comments else ""
                    }
                    
                    st.session_state.log_entries.append(entry)
                    save_entries()
                    st.session_state.form_data = {}
                    st.success("Form submitted successfully!")
                    
                    # Reset form-related session states
                    st.session_state.current_section = 1
                    st.session_state.member_verified = False
                    st.session_state.member_data = {}
                    st.session_state.service_date_checked = False
                    st.session_state.duplicate_service_date_confirmed = False
                    
                    # Change navigation to Member Login
                    st.session_state.nav_selection = "Member Login"
                    st.rerun()

elif st.session_state.nav_selection == "Support":
    st.markdown('<h1 class="main-title">Support</h1>', unsafe_allow_html=True)
    
    # Support page content
    st.markdown("""
    ### Contact Information
    - **Email:** sreevani.patil@focuscares.com
    - **Phone:** 1-XXX-XXX-XXXX
    
    ### Hours of Operation
    Monday - Friday: 9:00 AM - 5:00 PM MST
    
    
    ### Submit a Support Ticket
    """)
    
    # Support ticket form
    with st.form("support_ticket"):
        issue_type = st.selectbox(
            "Issue Type",
            ["Technical Problem", "Feature Request", "Data Issue", "Other"]
        )
        description = st.text_area("Description", height=150)
        priority = st.select_slider(
            "Priority",
            options=["Low", "Medium", "High", "Urgent"]
        )
        submitted = st.form_submit_button("Submit Ticket")
        
        if submitted:
            st.success("Support ticket submitted successfully!")

elif st.session_state.nav_selection == "Admin":
    # Check if user is admin
    if not st.session_state.is_admin:
        # Show admin login form
        st.markdown('<h1 class="main-title">Admin Login</h1>', unsafe_allow_html=True)
        
        # Center the login form
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            with st.form("admin_login"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Login")
                
                if submit:
                    # Check credentials
                    if username in ADMIN_CREDENTIALS:
                        hashed_password = hashlib.sha256(password.encode()).hexdigest()
                        if hashed_password == ADMIN_CREDENTIALS[username]:
                            st.session_state.is_admin = True
                            st.success("Login successful!")
                            st.rerun()
                        else:
                            st.error("Invalid password")
                    else:
                        st.error("Invalid username")
    else:
        
        # If no specific admin section is selected, show dashboard
        if not st.session_state.get('admin_selection'):
            # Create three columns for metrics
            col1, col2, col3 = st.columns(3)
            
            # Load log entries to calculate metrics
            try:
                with open('log_entries.json', 'r') as f:
                    log_entries = json.load(f)
                    
                # Calculate metrics
                total_forms = len(log_entries)
                
                # Count forms submitted today
                today = datetime.now().strftime("%Y-%m-%d")
                forms_today = sum(1 for entry in log_entries if entry.get('timestamp', '').startswith(today))
                
                # Count unique users (medicaid IDs)
                unique_users = len(set(entry.get('medicaid_id') for entry in log_entries if 'medicaid_id' in entry))
                
                # Display metrics
                with col1:
                    st.metric("Total Forms", total_forms)
                
                with col2:
                    st.metric("Forms Today", forms_today)
                
                with col3:
                    st.metric("Active Users", unique_users)
                    
            except (FileNotFoundError, json.JSONDecodeError):
                # If no entries file exists or is invalid
                with col1:
                    st.metric("Total Forms", 0)
                
                with col2:
                    st.metric("Forms Today", 0)
                
                with col3:
                    st.metric("Active Users", 0)
            
            # Remove the duplicate navigation buttons here

def read_excel_data(file_path: str) -> pd.DataFrame:
    """Read data from Excel file"""
    try:
        return pd.read_excel(file_path)
    except Exception as e:
        st.error(f"Error reading Excel file: {str(e)}")
        return pd.DataFrame()

def write_to_excel(data: dict, file_path: str) -> bool:
    """Write data to Excel file"""
    try:
        # Convert data to DataFrame
        df = pd.DataFrame([data])
        
        try:
            # Try to append to existing file
            book = load_workbook(file_path)
            with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
                df.to_excel(writer, index=False, header=False, startrow=writer.sheets['Sheet1'].max_row + 1)
        except FileNotFoundError:
            # Create new file if it doesn't exist
            df.to_excel(file_path, index=False)
        
        return True
    except Exception as e:
        st.error(f"Error writing to Excel file: {str(e)}")
        return False

# Add this at the beginning of your script with other session state initializations
if 'medicaid_id_to_update' not in st.session_state:
    st.session_state.medicaid_id_to_update = None

# After the service date confirmation check, add this debug information
if st.session_state.duplicate_service_date_confirmed:
    # Debug information
    # st.write(f"Current section: {st.session_state.current_section}")
    
    # Make sure form_data exists
    if 'form_data' not in st.session_state:
        st.session_state.form_data = {}
    
    # Section 1 (already implemented)
    if st.session_state.current_section == 1:
        # Your existing section 1 code
        pass
    
    # Section 2
    elif st.session_state.current_section == 2:
        with st.form("travel_form"):
            st.markdown('<h2 class="subheader">ADMINISTRATIVE TRAVEL DETAILS</h2>', unsafe_allow_html=True)
            
            st.markdown('<p class="section-number">2.1)</p>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                total_travel_time = st.number_input(
                    "TOTAL TRAVEL TIME (15 min increments)",
                    min_value=0.0,
                    max_value=24.0,
                    step=0.25
                )
            with col2:
                st.markdown("""
                **Decimal Conversion:**
                - 15 minutes = 0.25
                - 30 minutes = 0.50
                - 45 minutes = 0.75
                - 60 minutes = 1.00
                """)
            
            st.markdown('<p class="section-number">2.2)</p>', unsafe_allow_html=True)
            st.markdown("**OUTLINE EACH DESTINATION TO AND FROM LOCATIONS**")
            travel_locations = st.text_area(
                "Enter travel details",
                height=150,
                help="Please specify all locations visited in chronological order"
            )
            
            st.markdown('<p class="section-number">2.3)</p>', unsafe_allow_html=True)
            travel_comments = st.text_area(
                "Enter any additional comments",
                height=100,
                help="Add any relevant notes about the travel or visits"
            )

            submitted = st.form_submit_button("Next")
            if submitted:
                # Save section 2 data
                section_data = {
                    'total_travel_time': total_travel_time,
                    'travel_locations': travel_locations,
                    'travel_comments': travel_comments
                }
                
                # Update session state
                st.session_state.form_data.update(section_data)
                
                # Move to next section
                st.session_state.current_section += 1
                st.rerun()

    # Section 3
    elif st.session_state.current_section == 3:
        with st.form("tasks_form"):
            st.markdown('<h2 class="subheader">TASKS COMPLETED</h2>', unsafe_allow_html=True)
            
            st.markdown('<p class="section-number">3.1)</p>', unsafe_allow_html=True)
            tasks_completed_text = st.text_area(
                "TRANSITION COORDINATION TASK COMPLETED",
                height=150
            )
            
            st.markdown('<p class="section-number">3.2)</p>', unsafe_allow_html=True)
            next_steps = st.text_area(
                "NEXT STEPS/PLAN FOR FOLLOW UP",
                height=150
            )
            
            st.markdown('<p class="section-number">3.3)</p>', unsafe_allow_html=True)
            contact_types = st.multiselect(
                "TYPE OF CONTACT",
                options=["CALL", "EMAIL", "IN PERSON", "DOCUMENTATION", "Other"]
            )
            
            other_contact_type = None
            if "Other" in contact_types:
                st.markdown('<p class="section-number">3.3a)</p>', unsafe_allow_html=True)
                other_contact_type = st.text_input(
                    "Please specify other contact type(s)"
                )
            
            submitted = st.form_submit_button("Next")
            if submitted:
                # Save section 3 data
                section_data = {
                    'tasks_completed': tasks_completed_text,
                    'next_steps': next_steps,
                    'contact_types': contact_types
                }
                
                # Only add other_contact_type if it exists
                if other_contact_type:
                    section_data['other_contact_type'] = other_contact_type
                
                # Update session state
                st.session_state.form_data.update(section_data)
                
                # Move to next section
                st.session_state.current_section += 1
                st.rerun()

    # Section 4 (First Contact)
    elif st.session_state.current_section == 4:
        st.markdown('<h2 class="subheader">FIRST CONTACT</h2>', unsafe_allow_html=True)
        
        with st.form("first_contact_form"):  # Wrap in form
            st.markdown('<p class="section-number">4.1)</p>', unsafe_allow_html=True)
            first_contact_name = st.text_input("FULL NAME")
            
            st.markdown('<p class="section-number">4.2)</p>', unsafe_allow_html=True)
            first_contact_email = st.text_input("EMAIL")
            
            st.markdown('<p class="section-number">4.3)</p>', unsafe_allow_html=True)
            first_contact_phone = st.text_input(
                "PHONE NUMBER",
                help="Format: +1 XXX-XXX-XXXX (must include +1)",
                placeholder="+1 XXX-XXX-XXXX"
            )
            
            st.markdown('<p class="section-number">4.4)</p>', unsafe_allow_html=True)
            first_contact_outcome = st.radio(
                "OUTCOME",
                options=[
                    "DISCONNECTED/WRONG NUMBER",
                    "EMAIL",
                    "LEFT MESSAGE",
                    "NO ANSWER",
                    "SPOKE TO CONTACT",
                    "VOICEMAIL FULL",
                    "Other"
                ]
            )
            
            first_contact_other_outcome = None
            if first_contact_outcome == "Other":
                first_contact_other_outcome = st.text_input("Please specify other outcome")
            
            st.markdown('<p class="section-number">4.5)</p>', unsafe_allow_html=True)
            need_second_contact = st.radio(
                "Do you have another contact to enter?",
                ["Yes", "No"]
            )
            
            # Add the Next button inside the form
            submitted = st.form_submit_button("Next")
            if submitted:
                # Save the contact information to session state
                contact_data = {
                    'contact_name': first_contact_name,
                    'contact_email': first_contact_email,
                    'contact_phone': first_contact_phone,
                    'contact_outcome': first_contact_outcome
                }
                if first_contact_outcome == "Other" and first_contact_other_outcome:
                    contact_data['other_outcome'] = first_contact_other_outcome
                
                st.session_state.form_data.update({'first_contact': contact_data})
                
                # Determine next section based on need_second_contact
                if need_second_contact == "Yes":
                    st.session_state.current_section = 5  # Go to second contact
                else:
                    st.session_state.current_section = 8  # Skip to final section
                st.rerun()

    # Section 5 (Second Contact)
    elif st.session_state.current_section == 5:
        st.markdown('<h2 class="subheader">SECOND CONTACT</h2>', unsafe_allow_html=True)
        
        with st.form("second_contact_form_section5"):
            st.markdown('<p class="section-number">5.1)</p>', unsafe_allow_html=True)
            second_contact_name = st.text_input("FULL NAME", key="second_contact_name_sec5")
            
            st.markdown('<p class="section-number">5.2)</p>', unsafe_allow_html=True)
            second_contact_email = st.text_input("EMAIL", key="second_contact_email_sec5")
            
            st.markdown('<p class="section-number">5.3)</p>', unsafe_allow_html=True)
            second_contact_phone = st.text_input(
                "PHONE NUMBER",
                help="Format: +1 XXX-XXX-XXXX (must include +1)",
                placeholder="+1 XXX-XXX-XXXX",
                key="second_contact_phone_sec5"
            )
            
            st.markdown('<p class="section-number">5.4)</p>', unsafe_allow_html=True)
            second_contact_outcome = st.radio(
                "OUTCOME",
                options=[
                    "SPOKE TO CONTACT",
                    "LEFT MESSAGE",
                    "DISCONNECTED/WRONG NUMBER",
                    "NO ANSWER",
                    "VOICEMAIL FULL",
                    "Other"
                ],
                key="second_contact_outcome_sec5"
            )
            
            second_contact_other_outcome = None
            if second_contact_outcome == "Other":
                second_contact_other_outcome = st.text_input(
                    "Please specify other outcome (Second Contact)",
                    key="second_contact_other_outcome_sec5"
                )
            
            st.markdown('<p class="section-number">5.5)</p>', unsafe_allow_html=True)
            need_third_contact = st.radio(
                "Do you need to enter another contact?",
                ["Yes", "No"],
                key="need_third_contact_sec5"
            )
            
            submitted = st.form_submit_button("Next")
            if submitted:
                # Save contact information
                contact_data = {
                    'contact_name': second_contact_name,
                    'contact_email': second_contact_email,
                    'contact_phone': second_contact_phone,
                    'contact_outcome': second_contact_outcome
                }
                if second_contact_outcome == "Other" and second_contact_other_outcome:
                    contact_data['other_outcome'] = second_contact_other_outcome
                
                st.session_state.form_data.update({'second_contact': contact_data})
                
                # Navigate based on need_third_contact
                if need_third_contact == "Yes":
                    st.session_state.current_section = 6
                else:
                    st.session_state.current_section = 8
                st.rerun()

    # Section 6 (Third Contact)
    elif st.session_state.current_section == 6:
        st.markdown('<h2 class="subheader">THIRD CONTACT</h2>', unsafe_allow_html=True)
        
        with st.form("third_contact_form_section6"):
            st.markdown('<p class="section-number">6.1)</p>', unsafe_allow_html=True)
            third_contact_name = st.text_input("FULL NAME", key="third_contact_name_sec6")
            
            st.markdown('<p class="section-number">6.2)</p>', unsafe_allow_html=True)
            third_contact_email = st.text_input("EMAIL", key="third_contact_email_sec6")
            
            st.markdown('<p class="section-number">6.3)</p>', unsafe_allow_html=True)
            third_contact_phone = st.text_input(
                "PHONE NUMBER",
                help="Format: +1 XXX-XXX-XXXX (must include +1)",
                placeholder="+1 XXX-XXX-XXXX",
                key="third_contact_phone_sec6"
            )
            
            st.markdown('<p class="section-number">6.4)</p>', unsafe_allow_html=True)
            third_contact_outcome = st.radio(
                "OUTCOME",
                options=[
                    "SPOKE TO CONTACT",
                    "LEFT MESSAGE",
                    "DISCONNECTED/WRONG NUMBER",
                    "NO ANSWER",
                    "VOICEMAIL FULL",
                    "Other"
                ],
                key="third_contact_outcome_sec6"
            )
            
            third_contact_other_outcome = None
            if third_contact_outcome == "Other":
                third_contact_other_outcome = st.text_input(
                    "Please specify other outcome (Third Contact)",
                    key="third_contact_other_outcome_sec6"
                )
            
            st.markdown('<p class="section-number">6.5)</p>', unsafe_allow_html=True)
            need_fourth_contact = st.radio(
                "Do you need to enter another contact?",
                ["Yes", "No"],
                key="need_fourth_contact_sec6"
            )
            
            submitted = st.form_submit_button("Next")
            if submitted:
                # Save contact information
                contact_data = {
                    'contact_name': third_contact_name,
                    'contact_email': third_contact_email,
                    'contact_phone': third_contact_phone,
                    'contact_outcome': third_contact_outcome
                }
                if third_contact_outcome == "Other" and third_contact_other_outcome:
                    contact_data['other_outcome'] = third_contact_other_outcome
                
                st.session_state.form_data.update({'third_contact': contact_data})
                
                # Navigate based on need_fourth_contact
                if need_fourth_contact == "Yes":
                    st.session_state.current_section = 7
                else:
                    st.session_state.current_section = 8
                st.rerun()

    # Section 7 (Fourth Contact)
    elif st.session_state.current_section == 7:
        st.markdown('<h2 class="subheader">FOURTH CONTACT</h2>', unsafe_allow_html=True)
        
        with st.form("fourth_contact_form_section7"):
            st.markdown('<p class="section-number">7.1)</p>', unsafe_allow_html=True)
            fourth_contact_name = st.text_input("FULL NAME", key="fourth_contact_name_sec7")
            
            st.markdown('<p class="section-number">7.2)</p>', unsafe_allow_html=True)
            fourth_contact_email = st.text_input("EMAIL", key="fourth_contact_email_sec7")
            
            st.markdown('<p class="section-number">7.3)</p>', unsafe_allow_html=True)
            fourth_contact_phone = st.text_input(
                "PHONE NUMBER",
                help="Format: +1 XXX-XXX-XXXX (must include +1)",
                placeholder="+1 XXX-XXX-XXXX",
                key="fourth_contact_phone_sec7"
            )
            
            st.markdown('<p class="section-number">7.4)</p>', unsafe_allow_html=True)
            fourth_contact_outcome = st.radio(
                "OUTCOME",
                options=[
                    "SPOKE TO CONTACT",
                    "LEFT MESSAGE",
                    "DISCONNECTED/WRONG NUMBER",
                    "NO ANSWER",
                    "VOICEMAIL FULL",
                    "Other"
                ],
                key="fourth_contact_outcome_sec7"
            )
            
            fourth_contact_other_outcome = None
            if fourth_contact_outcome == "Other":
                fourth_contact_other_outcome = st.text_input(
                    "Please specify other outcome (Fourth Contact)",
                    key="fourth_contact_other_outcome_sec7"
                )
            
            submitted = st.form_submit_button("Next")
            if submitted:
                # Save contact information
                contact_data = {
                    'contact_name': fourth_contact_name,
                    'contact_email': fourth_contact_email,
                    'contact_phone': fourth_contact_phone,
                    'contact_outcome': fourth_contact_outcome
                }
                if fourth_contact_outcome == "Other" and fourth_contact_other_outcome:
                    contact_data['other_outcome'] = fourth_contact_other_outcome
                
                st.session_state.form_data.update({'fourth_contact': contact_data})
                
                # Move to final section
                st.session_state.current_section = 8
                st.rerun()

    # Section 8 (Final Section)
    elif st.session_state.current_section == 8:
        st.markdown('<h2 class="subheader">ADMINISTRATIVE COMMENTS</h2>', unsafe_allow_html=True)
        
        with st.form("final_form_section8"):
            st.markdown('<p class="section-number">8.1)</p>', unsafe_allow_html=True)
            st.markdown("**PLEASE ENTER ADMINISTRATIVE WORK COMPLETED**")
            admin_comments = st.text_area(
                "Enter administrative work details",
                height=200,
                help="Provide details about the administrative work completed",
                key="admin_comments_sec8"
            )
            
            submitted = st.form_submit_button("Submit")
            if submitted:
                # Handle final submission
                # Create the entry with all fields as they are
                entry = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    **st.session_state.form_data,
                    "admin_comments": admin_comments if admin_comments else ""
                }
                
                st.session_state.log_entries.append(entry)
                save_entries()
                st.session_state.form_data = {}
                st.success("Form submitted successfully!")
                
                # Reset form-related session states
                st.session_state.current_section = 1
                st.session_state.member_verified = False
                st.session_state.member_data = {}
                st.session_state.service_date_checked = False
                st.session_state.duplicate_service_date_confirmed = False
                
                # Change navigation to Member Login
                st.session_state.nav_selection = "Member Login"
                st.rerun()
