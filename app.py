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


def get_member_details(medicaid_id: str) -> dict:
    """
    Get member details from master database
    Returns dictionary with member information
    """
    try:
        # Check if file exists
        excel_path = './Master_db.xlsx'
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
            st.warning(f"No record found for Medicaid ID: {medicaid_id}")
            return {}
        
        # Get the member data
        member = df[member_mask].iloc[0]
        
        member_data = {
            'member_name': f"{member['FIRST NAME']} {member['LAST NAME']}",
            'member_dob': member['DOB']
        }
        
        return member_data
        
    except Exception as e:
        st.error(f"Error in get_member_details: {str(e)}")
        print(f"Error in get_member_details: {str(e)}")  # Debug log
        return {}

# Set page configuration
st.set_page_config(
    page_title="2025 Colorado Transition Coordinator Log Notes",
    page_icon="📝",
    layout="wide"
)

# Initialize session state for storing log entries
if 'log_entries' not in st.session_state:
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

# Initialize nav_selection if not in session state
if 'nav_selection' not in st.session_state:
    st.session_state.nav_selection = "Submit New Form"

# Add CSS for button styling
st.markdown("""
<style>
    /* Remove default button styling for admin options */
    .admin-options .stButton > button {
        width: 100%;
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: #000000;
        text-align: left;
        padding: 0.5rem 1rem;
        margin: 0.2rem 0;
    }
    
    /* Selected state for admin options */
    .admin-options .stButton > button.selected {
        color: #0096FF !important;
        font-weight: 500;
    }
    
    /* Hover state for admin options */
    .admin-options .stButton > button:hover {
        color: #0096FF !important;
        background-color: #f0f2f6 !important;
    }
    
    /* Remove orange/red background from selected button */
    .admin-options .stButton > button[kind="secondary"] {
        background-color: transparent !important;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar navigation
with st.sidebar:
    # Logo
    st.image("https://focuscares.com/wp-content/uploads/elementor/thumbs/logo-pcsu71jmplrr1f3b7mtv083rbyula7p5imfik70y8o.png", width=200)
    
    st.markdown("---")  # Separator line
    
    # Main navigation buttons
    if st.button("Submit New Form", 
                 key="nav_submit", 
                 use_container_width=True,
                 type="primary" if st.session_state.nav_selection == "Submit New Form" else "secondary"):
        st.session_state.nav_selection = "Submit New Form"
        st.session_state.admin_selection = None
        st.rerun()
        
    if st.button("Support", 
                 key="nav_support", 
                 use_container_width=True,
                 type="primary" if st.session_state.nav_selection == "Support" else "secondary"):
        st.session_state.nav_selection = "Support"
        st.session_state.admin_selection = None
        st.rerun()
        
    if st.button("Admin", 
                 key="nav_admin", 
                 use_container_width=True,
                 type="primary" if st.session_state.nav_selection == "Admin" else "secondary"):
        st.session_state.nav_selection = "Admin"
        st.rerun()

    # Show admin options if Admin is selected
    if st.session_state.nav_selection == "Admin" and st.session_state.is_admin:
        st.markdown("### Admin Options")
        st.markdown('<div class="admin-options">', unsafe_allow_html=True)
        
        # Admin sub-navigation buttons
        if st.button(
            "View Submitted Forms",
            key="admin_view",
            use_container_width=True,
            type="secondary"
        ):
            st.session_state.admin_selection = "View Submitted Forms"
            st.rerun()
        
        if st.button(
            "Update Info",
            key="admin_update",
            use_container_width=True,
            type="secondary"
        ):
            st.session_state.admin_selection = "Update Info"
            st.rerun()
        
        if st.button(
            "Process Claims",
            key="admin_claims",
            use_container_width=True,
            type="secondary"
        ):
            st.session_state.admin_selection = "Process Claims"
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

# Main content area based on navigation
if st.session_state.nav_selection == "Submit New Form":
    # Main title with custom class
    st.markdown('<h1 class="main-title">2025 Colorado Transition Coordinator Log Notes</h1>', unsafe_allow_html=True)
    
    # Add initial ID input before showing the full form
    with st.form("member_form"):
        st.markdown("### Member Information")
        medicaid_id = st.text_input(
            "Enter Medicaid ID",
            help="Medicaid ID must be 7 characters: first character must be a letter, followed by letters or numbers",
            placeholder="Example: A123456"
        )
        fill_form_submitted = st.form_submit_button("Fill Form")
    
    # Handle form submission outside the form
    if fill_form_submitted:
        if not medicaid_id:
            st.error("Please enter a Medicaid ID")
        else:
            # Validate format only
            is_valid, error_msg = validate_medicaid_id(medicaid_id)
            if not is_valid:
                st.error(error_msg)
            else:
                st.markdown(
                    """
                    <div style='padding: 1rem; background-color: #e6f3ff; border-radius: 0.5rem; color: #0d47a1;'>
                        Medicaid ID format is valid. Please proceed with filling out the form.
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                st.session_state.member_verified = True
                st.session_state.member_data = {'medicaid_id': medicaid_id}
                st.session_state.current_section = 1  # Start at section 1
                st.rerun()

# Only show the form sections if member is verified
if st.session_state.member_verified:
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

    # Progress bar with custom styling
    st.markdown(create_progress_bar(st.session_state.current_section, TOTAL_SECTIONS), unsafe_allow_html=True)
    st.markdown(f'<p class="progress-text">Section {st.session_state.current_section} of {TOTAL_SECTIONS}</p>', unsafe_allow_html=True)

    def save_entries():
        """Save entries to a JSON file with date serialization"""
        try:
            serializable_entries = []
            for entry in st.session_state.log_entries:
                serializable_entry = {}
                for key, value in entry.items():
                    # Convert date objects to string format
                    if isinstance(value, (datetime, date)):
                        serializable_entry[key] = value.strftime("%Y-%m-%d")
                    else:
                        serializable_entry[key] = value
                serializable_entries.append(serializable_entry)
            
            with open('log_entries.json', 'w') as f:
                json.dump(serializable_entries, f, indent=4)
            
            print(f"Saved {len(serializable_entries)} entries to log_entries.json")  # Debug print
        except Exception as e:
            print(f"Error saving entries: {str(e)}")  # Debug print

    def load_entries():
        """Load entries from JSON file and parse dates"""
        try:
            with open('log_entries.json', 'r') as f:
                entries = json.load(f)
                
                # Convert date strings back to date objects
                for entry in entries:
                    if 'service_date' in entry:
                        entry['service_date'] = datetime.strptime(entry['service_date'], "%Y-%m-%d").date()
                    if 'member_dob' in entry:
                        entry['member_dob'] = datetime.strptime(entry['member_dob'], "%Y-%m-%d").date()
                
                st.session_state.log_entries = entries
        except FileNotFoundError:
            st.session_state.log_entries = []

    # Navigation buttons (outside any form)
    cols = st.columns([2, 2, 8])
    with cols[0]:
        if st.session_state.current_section > 1:
            if st.button("Previous"):
                st.session_state.current_section -= 1
                st.rerun()

    # Pre-fill form with member data where applicable
    member_data = st.session_state.member_data
    
    # Form for each section
    if st.session_state.current_section == 3:  # Tasks Completed section
        with st.form("tasks_form"):
            st.markdown('<h2 class="subheader">TASKS COMPLETED</h2>', unsafe_allow_html=True)
            
            st.markdown("**TRANSITION COORDINATION TASK COMPLETED**")
            tasks_completed = st.text_area(
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

            # Submit button at the end of the form
            submitted = st.form_submit_button("Next")
            if submitted:
                # Save section 3 data
                section_data = {
                    'tasks_completed': tasks_completed,
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

    # Similar structure for other sections
    elif st.session_state.current_section == 1:
        with st.form("demographics_form"):
            st.markdown('<h2 class="subheader">DEMOGRAPHICS</h2>', unsafe_allow_html=True)
            
            # Get medicaid_id from session state
            medicaid_id = st.session_state.member_data.get('medicaid_id', '')
            
            # Get member details if available
            member_details = get_member_details(medicaid_id) if medicaid_id else {}
            
            medicaid_id_display = st.text_input(
                "MEDICAID ID *",
                value=medicaid_id,
                disabled=True,  # Make non-editable
                key="medicaid_id_display"
            )
            
            member_name = st.text_input(
                "MEMBER NAME *",
                value=member_details.get('member_name', ''),
                disabled=True if member_details else False,
                key="member_name"
            )
            
            if member_details.get('member_dob'):
                member_dob = st.date_input(
                    "MEMBER DOB *",
                    value=pd.to_datetime(member_details['member_dob']).date(),
                    disabled=True,
                    key="member_dob"
                )
            else:
                member_dob = st.date_input(
                    "MEMBER DOB *",
                    value=None,
                    key="member_dob"
                )

            st.markdown('<p class="section-number">1.1)</p>', unsafe_allow_html=True)

            member_id = st.text_input("MEMBER ID", key="member_id", help="Member ID must be a numerical value")
            st.markdown('<p class="section-number">1.2)</p>', unsafe_allow_html=True)
            note_type = st.radio(
                "Is this a new note or an amendment to correct a previous note?",
                ["New Note", "Amendment"]
            )
            
            if note_type == "Amendment":
                st.markdown('<p class="section-number">1.2a)</p>', unsafe_allow_html=True)
                st.markdown("""
                **REASON FOR FORM AMENDMENT**""")
                amendment_reason = st.text_area(
                    "Enter your reason for amendment",
                    height=100,
                    key="amendment_reason"
                )
            
            st.markdown('<p class="section-number">1.3)</p>', unsafe_allow_html=True)
            service_date = st.date_input("DATE OF SERVICE")
            
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
            
            st.markdown('<p class="section-number">1.5)</p>', unsafe_allow_html=True)
            
            # Create the note category radio
            note_category = st.radio(
                "Type of Note", 
                ["Administrative", "Billable- TCM"],
                key="note_category"
            )
            
            # Create a container for admin type options
            admin_type_container = st.container()
            
            # Show Administrative Type options if Administrative is selected
            if note_category == "Administrative":
                with admin_type_container:
                    st.markdown('<p class="section-number">1.5a)</p>', unsafe_allow_html=True)
                    st.markdown("**Administrative Type**")  # Add a clear header
                    admin_type = st.radio(
                        "Select Administrative Type",
                        options=["MEETING", "Training", "Travel"],
                        key="admin_type_radio",
                        label_visibility="collapsed"  # Hide the label since we have the header
                    )
            
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
                ["T1017 TRANSITION COORDINATION",
                 "T2038 HOUSEHOLD SET UP TIME",
                 "Administrative",
                 "PASRR Options Counseling"]
            )

            submitted = st.form_submit_button("Next")
            if submitted:
                if not member_id.strip():
                    st.error("Member ID is required. Please enter a Member ID before proceeding.")
                elif not member_id.strip().isnumeric():
                    st.error("Member ID must contain only numbers. Please enter a valid numerical Member ID.")
                else:
                    # Save the form data and proceed
                    form_data = {
                        'medicaid_id': medicaid_id,
                        'member_name': member_name,
                        'member_id': member_id,
                        'member_dob': member_dob,
                        'note_type': note_type,
                        'service_date': service_date,
                        'travel_to_client': travel_to_client
                    }
                    st.session_state.form_data.update(form_data)
                    st.session_state.current_section = 2
                    st.rerun()

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
                if first_contact_outcome == "Other":
                    contact_data['other_outcome'] = first_contact_other_outcome
                
                st.session_state.form_data.update({'first_contact': contact_data})
                
                # Determine next section based on need_second_contact
                if need_second_contact == "Yes":
                    st.session_state.current_section = 5  # Go to second contact
                else:
                    st.session_state.current_section = 8  # Skip to final section
                st.rerun()

    elif st.session_state.current_section == 5:  # Second Contact
        with st.form("second_contact_form"):
            st.markdown('<h2 class="subheader">SECOND CONTACT</h2>', unsafe_allow_html=True)
            
            st.markdown('<p class="section-number">5.1)</p>', unsafe_allow_html=True)
            second_contact_name = st.text_input("FULL NAME")
            
            st.markdown('<p class="section-number">5.2)</p>', unsafe_allow_html=True)
            second_contact_email = st.text_input("EMAIL")
            
            st.markdown('<p class="section-number">5.3)</p>', unsafe_allow_html=True)
            second_contact_phone = st.text_input(
                "PHONE NUMBER",
                help="Format: +1 XXX-XXX-XXXX (must include +1)",
                placeholder="+1 XXX-XXX-XXXX"
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
                ]
            )
            
            if second_contact_outcome == "Other":
                second_contact_other_outcome = st.text_input("Please specify other outcome (Second Contact)")
            
            st.markdown('<p class="section-number">5.5)</p>', unsafe_allow_html=True)
            need_third_contact = st.radio(
                "Do you need to enter another contact?",
                ["Yes", "No"]
            )
            
            # Add Next button
            submitted = st.form_submit_button("Next")
            if submitted:
                # Save contact information
                contact_data = {
                    'contact_name': second_contact_name,
                    'contact_email': second_contact_email,
                    'contact_phone': second_contact_phone,
                    'contact_outcome': second_contact_outcome
                }
                if second_contact_outcome == "Other":
                    contact_data['other_outcome'] = second_contact_other_outcome
                
                st.session_state.form_data.update({'second_contact': contact_data})
                
                # Navigate based on need_third_contact
                if need_third_contact == "Yes":
                    st.session_state.current_section = 6
                else:
                    st.session_state.current_section = 8
                st.rerun()

    elif st.session_state.current_section == 6:  # Third Contact
        with st.form("third_contact_form"):
            st.markdown('<h2 class="subheader">THIRD CONTACT</h2>', unsafe_allow_html=True)
            
            st.markdown('<p class="section-number">6.1)</p>', unsafe_allow_html=True)
            third_contact_name = st.text_input("FULL NAME")
            
            st.markdown('<p class="section-number">6.2)</p>', unsafe_allow_html=True)
            third_contact_email = st.text_input("EMAIL")
            
            st.markdown('<p class="section-number">6.3)</p>', unsafe_allow_html=True)
            third_contact_phone = st.text_input(
                "PHONE NUMBER",
                help="Format: +1 XXX-XXX-XXXX (must include +1)",
                placeholder="+1 XXX-XXX-XXXX"
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
                ]
            )
            
            if third_contact_outcome == "Other":
                third_contact_other_outcome = st.text_input("Please specify other outcome (Third Contact)")
            
            st.markdown('<p class="section-number">6.5)</p>', unsafe_allow_html=True)
            need_fourth_contact = st.radio(
                "Do you need to enter another contact?",
                ["Yes", "No"]
            )
            
            # Add Next button
            submitted = st.form_submit_button("Next")
            if submitted:
                # Save contact information
                contact_data = {
                    'contact_name': third_contact_name,
                    'contact_email': third_contact_email,
                    'contact_phone': third_contact_phone,
                    'contact_outcome': third_contact_outcome
                }
                if third_contact_outcome == "Other":
                    contact_data['other_outcome'] = third_contact_other_outcome
                
                st.session_state.form_data.update({'third_contact': contact_data})
                
                # Navigate based on need_fourth_contact
                if need_fourth_contact == "Yes":
                    st.session_state.current_section = 7
                else:
                    st.session_state.current_section = 8
                st.rerun()

    elif st.session_state.current_section == 7:  # Fourth Contact
        with st.form("fourth_contact_form"):
            st.markdown('<h2 class="subheader">FOURTH CONTACT</h2>', unsafe_allow_html=True)
            
            st.markdown('<p class="section-number">7.1)</p>', unsafe_allow_html=True)
            fourth_contact_name = st.text_input("FULL NAME")
            
            st.markdown('<p class="section-number">7.2)</p>', unsafe_allow_html=True)
            fourth_contact_email = st.text_input("EMAIL")
            
            st.markdown('<p class="section-number">7.3)</p>', unsafe_allow_html=True)
            fourth_contact_phone = st.text_input(
                "PHONE NUMBER",
                help="Format: +1 XXX-XXX-XXXX (must include +1)",
                placeholder="+1 XXX-XXX-XXXX"
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
                ]
            )
            
            if fourth_contact_outcome == "Other":
                fourth_contact_other_outcome = st.text_input("Please specify other outcome (Fourth Contact)")
            
            # Add Next button
            submitted = st.form_submit_button("Next")
            if submitted:
                # Save contact information
                contact_data = {
                    'contact_name': fourth_contact_name,
                    'contact_email': fourth_contact_email,
                    'contact_phone': fourth_contact_phone,
                    'contact_outcome': fourth_contact_outcome
                }
                if fourth_contact_outcome == "Other":
                    contact_data['other_outcome'] = fourth_contact_other_outcome
                
                st.session_state.form_data.update({'fourth_contact': contact_data})
                
                # Move to final section
                st.session_state.current_section = 8
                st.rerun()

    elif st.session_state.current_section == 8:
        with st.form("final_form"):
            st.markdown('<h2 class="subheader">ADMINISTRATIVE COMMENTS</h2>', unsafe_allow_html=True)
            
            st.markdown('<p class="section-number">8.1)</p>', unsafe_allow_html=True)
            st.markdown("**PLEASE ENTER ADMINISTRATIVE WORK COMPLETED**")
            admin_comments = st.text_area(
                "Enter administrative work details",
                height=200,
                help="Provide details about the administrative work completed"
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
                
                # Change navigation to View Submitted Forms
                st.session_state.nav_selection = "View Submitted Forms"
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
    if not st.session_state.is_admin:
        st.markdown('<h1 class="main-title">Admin Login</h1>', unsafe_allow_html=True)
        
        # Center the login form
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            with st.form("admin_login"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Login")
                
                if submit:
                    if username in ADMIN_CREDENTIALS and \
                       ADMIN_CREDENTIALS[username] == hashlib.sha256(password.encode()).hexdigest():
                        st.session_state.is_admin = True
                        st.success("Login successful!")
                        time.sleep(1)  # Brief pause before rerun
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
    
    else:  # User is logged in as admin
        # Show admin content based on selection
        if not st.session_state.get('admin_selection'):
            st.markdown('<h1 class="main-title">Admin Dashboard</h1>', unsafe_allow_html=True)
            st.markdown("### Please select an option from the sidebar menu")
            
            # Display some admin stats or overview
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Forms", "150")
            with col2:
                st.metric("Forms Today", "12")
            with col3:
                st.metric("Active Users", "25")
        
        elif st.session_state.admin_selection == "View Submitted Forms":
            st.markdown('<h1 class="main-title">View Submitted Forms</h1>', unsafe_allow_html=True)
            
            # Load all forms from the JSON file
            try:
                with open('log_entries.json', 'r') as f:
                    all_forms = json.load(f)
            except FileNotFoundError:
                all_forms = []
            
            # Date filter section
            with st.expander("Filter by Date"):
                col1, col2 = st.columns(2)
                with col1:
                    start_date = st.date_input("Start Date")
                with col2:
                    end_date = st.date_input("End Date")
                
                if st.button("Apply Filter"):
                    # Filter forms by date range
                    filtered_forms = [
                        form for form in all_forms 
                        if start_date <= datetime.strptime(form['service_date'], "%Y-%m-%d").date() <= end_date
                    ]
                else:
                    filtered_forms = all_forms

            # Display forms in a table
            if filtered_forms:
                # Convert to DataFrame for better display
                df = pd.DataFrame(filtered_forms)
                
                # Reorder and rename columns for display
                columns_to_display = {
                    'service_date': 'Service Date',
                    'medicaid_id': 'Medicaid ID',
                    'member_name': 'Member Name',
                    'member_id': 'Member ID',
                    'member_dob': 'Date of Birth',
                    'contact_types': 'Contact Types'
                }
                
                df_display = df[[col for col in columns_to_display.keys() if col in df.columns]]
                df_display.columns = [columns_to_display[col] for col in df_display.columns]
                
                # Format dates (both service_date and DOB)
                if 'Service Date' in df_display.columns:
                    df_display['Service Date'] = pd.to_datetime(df_display['Service Date']).dt.strftime('%Y-%m-%d')
                if 'Date of Birth' in df_display.columns:
                    df_display['Date of Birth'] = pd.to_datetime(df_display['Date of Birth']).dt.strftime('%Y-%m-%d')
                
                # Display the table
                st.dataframe(
                    df_display,
                    use_container_width=True,
                    hide_index=True
                )
                
                # Create Excel file in memory
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                    
                    # Get the worksheet
                    worksheet = writer.sheets['Sheet1']
                    
                    # Define styles
                    header_style = NamedStyle(name='header_style')
                    header_style.font = Font(bold=True)
                    header_style.fill = PatternFill(start_color='FFFF00', end_color='FFFF00', fill_type='solid')
                    
                    # Apply formatting to headers and set column widths
                    for col in range(len(df.columns)):
                        cell = worksheet.cell(row=1, column=col + 1)
                        cell.style = header_style
                        
                        # Enable text wrapping for all cells in the column
                        column = worksheet.column_dimensions[get_column_letter(col + 1)]
                        for row in range(2, len(df) + 2):  # Start from row 2 to skip header
                            cell = worksheet.cell(row=row, column=col + 1)
                            cell.alignment = Alignment(wrap_text=True, vertical='top')
                        
                        # Set reasonable column width
                        column.width = 30  # Fixed width for better readability
                    
                    # Set row height to accommodate wrapped text
                    for row in worksheet.iter_rows(min_row=2, max_row=len(df) + 1):
                        worksheet.row_dimensions[row[0].row].height = 45
                    
                    # Add borders to all cells
                    thin_border = Border(
                        left=Side(style='thin'),
                        right=Side(style='thin'),
                        top=Side(style='thin'),
                        bottom=Side(style='thin')
                    )
                    
                    for row in worksheet.iter_rows(min_row=1, max_row=len(df) + 1):
                        for cell in row:
                            cell.border = thin_border
                
                # Single Export button that triggers download
                st.download_button(
                    label="Export to Excel",
                    data=output.getvalue(),
                    file_name=f"submitted_forms_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.info("No forms found for the selected criteria")

        elif st.session_state.admin_selection == "Update Info":
            st.markdown('<h1 class="main-title">Update Information</h1>', unsafe_allow_html=True)
            
            # Member search
            search_id = st.text_input("Enter Member ID or Medicaid ID")
            if st.button("Search"):
                # Add your member search logic here
                st.write("Member information will appear here")
            
            # Update form would appear after search
            
        elif st.session_state.admin_selection == "Process Claims":
            st.markdown('<h1 class="main-title">Process Claims</h1>', unsafe_allow_html=True)
            
            # Claims processing interface
            st.markdown("### Claims Dashboard")
            
            # Updated tab names
            tab1, tab2, tab3 = st.tabs(["Demograph", "TCM", "LST"])
            
            with tab1:
                try:
                    # Read Excel file
                    excel_path = './Master_db.xlsx'
                    if not Path(excel_path).exists():
                        st.error(f"Excel file not found at: {excel_path}")
                    else:
                        df = pd.read_excel(excel_path)
                        
                        # Add search functionality
                        search_col1, search_col2 = st.columns([2,1])
                        with search_col1:
                            search_term = st.text_input("Search by Medicaid ID or Name")
                        
                        # Filter dataframe if search term is entered
                        if search_term:
                            mask = (
                                df['MedicaidID'].astype(str).str.contains(search_term, case=False) |
                                df['FIRST NAME'].astype(str).str.contains(search_term, case=False) |
                                df['LAST NAME'].astype(str).str.contains(search_term, case=False)
                            )
                            filtered_df = df[mask]
                        else:
                            filtered_df = df
                        
                        # Display the data
                        st.dataframe(
                            filtered_df,
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        # Export functionality
                        if st.button("Export Demograph Data"):
                            # Create Excel file in memory
                            output = BytesIO()
                            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                filtered_df.to_excel(writer, index=False)
                                
                                # Get the worksheet
                                worksheet = writer.sheets['Sheet1']
                                
                                # Define styles
                                header_style = NamedStyle(name='header_style')
                                header_style.font = Font(bold=True)
                                header_style.fill = PatternFill(start_color='FFFF00', end_color='FFFF00', fill_type='solid')
                                
                                # Apply formatting
                                for col in range(len(filtered_df.columns)):
                                    cell = worksheet.cell(row=1, column=col + 1)
                                    cell.style = header_style
                                    
                                    # Enable text wrapping
                                    column = worksheet.column_dimensions[get_column_letter(col + 1)]
                                    for row in range(2, len(filtered_df) + 2):
                                        cell = worksheet.cell(row=row, column=col + 1)
                                        cell.alignment = Alignment(wrap_text=True, vertical='top')
                                    
                                    # Set column width
                                    column.width = 30
                                
                                # Set row height
                                for row in worksheet.iter_rows(min_row=2, max_row=len(filtered_df) + 1):
                                    worksheet.row_dimensions[row[0].row].height = 45
                                
                                # Add borders
                                thin_border = Border(
                                    left=Side(style='thin'),
                                    right=Side(style='thin'),
                                    top=Side(style='thin'),
                                    bottom=Side(style='thin')
                                )
                                
                                for row in worksheet.iter_rows(min_row=1, max_row=len(filtered_df) + 1):
                                    for cell in row:
                                        cell.border = thin_border
                            
                            # Download button
                            st.download_button(
                                label="Download Excel file",
                                data=output.getvalue(),
                                file_name=f"demograph_data_{datetime.now().strftime('%Y%m%d')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                            
                except Exception as e:
                    st.error(f"Error loading data: {str(e)}")
                    print(f"Error loading data: {str(e)}")  # Debug log
            
            with tab2:
                st.write("TCM data will appear here")
                # Add your TCM data table/list
                
            with tab3:
                st.write("LST data will appear here")
                # Add your LST data table/list

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
