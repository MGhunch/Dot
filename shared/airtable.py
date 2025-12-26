# Dot Shared Airtable Functions
# All Airtable read/write operations

import httpx
from datetime import date
from .config import AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_CLIENTS_TABLE, AIRTABLE_PROJECTS_TABLE, AIRTABLE_UPDATES_TABLE
from .helpers import get_next_working_day


def _get_headers():
    """Get standard Airtable headers"""
    return {
        'Authorization': f'Bearer {AIRTABLE_API_KEY}',
        'Content-Type': 'application/json'
    }


# ===================
# READ OPERATIONS
# ===================

def get_project_by_job_number(job_number):
    """Look up existing project by job number.
    
    Returns project details dict or None if not found.
    Used by Traffic to validate job numbers and enrich routing data.
    """
    if not AIRTABLE_API_KEY:
        print("No Airtable API key configured")
        return None
    
    try:
        search_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_PROJECTS_TABLE}"
        params = {'filterByFormula': f"{{Job Number}}='{job_number}'"}
        
        response = httpx.get(search_url, headers=_get_headers(), params=params, timeout=10.0)
        response.raise_for_status()
        
        records = response.json().get('records', [])
        
        if not records:
            print(f"Job '{job_number}' not found in Airtable")
            return None
        
        record = records[0]
        fields = record['fields']
        
        # Get client name from linked record if available
        client_name = fields.get('Client', '')
        if isinstance(client_name, list):
            client_name = client_name[0] if client_name else ''
        
        return {
            'recordId': record['id'],
            'jobNumber': fields.get('Job Number', job_number),
            'jobName': fields.get('Project Name', ''),
            'clientName': client_name,
            'stage': fields.get('Stage', ''),
            'status': fields.get('Status', ''),
            'round': fields.get('Round', 0) or 0,
            'withClient': fields.get('With Client?', False),
            'teamsChannelId': fields.get('Teams Channel ID', None)
        }
        
    except Exception as e:
        print(f"Error looking up project in Airtable: {e}")
        return None


def get_client_by_code(client_code):
    """Look up client by code.
    
    Returns client details including Teams ID, SharePoint URL, next job number.
    Used by Triage when creating new jobs.
    """
    if not AIRTABLE_API_KEY:
        print("No Airtable API key configured")
        return None
    
    try:
        search_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_CLIENTS_TABLE}"
        params = {'filterByFormula': f"{{Client code}}='{client_code}'"}
        
        response = httpx.get(search_url, headers=_get_headers(), params=params, timeout=10.0)
        response.raise_for_status()
        
        records = response.json().get('records', [])
        
        if not records:
            print(f"Client code '{client_code}' not found in Airtable")
            return None
        
        record = records[0]
        fields = record['fields']
        
        return {
            'recordId': record['id'],
            'clientCode': client_code,
            'clientName': fields.get('Client', ''),
            'teamsId': fields.get('Teams ID', None),
            'sharepointUrl': fields.get('Sharepoint ID', None),
            'nextNumber': fields.get('Next #', 1)
        }
        
    except Exception as e:
        print(f"Error looking up client in Airtable: {e}")
        return None


def get_active_jobs_for_client(client_code):
    """Get all active (In Progress, On Hold) jobs for a client.
    
    Returns list of job summaries for matching against.
    Used by Traffic when trying to match emails to jobs.
    """
    if not AIRTABLE_API_KEY:
        print("No Airtable API key configured")
        return []
    
    try:
        # Filter by client code prefix in Job Number and active status
        filter_formula = f"AND(FIND('{client_code}', {{Job Number}})=1, OR({{Status}}='In Progress', {{Status}}='On Hold'))"
        
        search_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_PROJECTS_TABLE}"
        params = {'filterByFormula': filter_formula}
        
        response = httpx.get(search_url, headers=_get_headers(), params=params, timeout=10.0)
        response.raise_for_status()
        
        records = response.json().get('records', [])
        
        jobs = []
        for record in records:
            fields = record['fields']
            jobs.append({
                'jobNumber': fields.get('Job Number', ''),
                'jobName': fields.get('Project Name', ''),
                'description': fields.get('Description', '')
            })
        
        return jobs
        
    except Exception as e:
        print(f"Error getting active jobs for client: {e}")
        return []


# ===================
# WRITE OPERATIONS
# ===================

def increment_client_job_number(client_code):
    """Increment and return the next job number for a client.
    
    Returns formatted job number (e.g., 'TOW 023') or 'TBC' on failure.
    Also returns Teams ID, SharePoint URL, and client record ID.
    """
    if not AIRTABLE_API_KEY:
        print("No Airtable API key configured")
        return f"{client_code} TBC", None, None, None
    
    try:
        client = get_client_by_code(client_code)
        
        if not client:
            return f"{client_code} TBC", None, None, None
        
        current_number = client['nextNumber']
        next_number = current_number + 1
        
        # Format job number (e.g., "TOW 023")
        job_number = f"{client_code} {str(current_number).zfill(3)}"
        
        # Update Airtable with incremented number
        update_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_CLIENTS_TABLE}/{client['recordId']}"
        update_data = {'fields': {'Next #': next_number}}
        
        httpx.patch(update_url, headers=_get_headers(), json=update_data, timeout=10.0)
        
        return job_number, client['teamsId'], client['sharepointUrl'], client['recordId']
        
    except Exception as e:
        print(f"Error incrementing job number: {e}")
        return f"{client_code} TBC", None, None, None


def create_project(job_number, job_name, description, project_owner, client_record_id):
    """Create a new project record.
    
    Used by Triage when setting up new jobs.
    Returns the new record ID or None on failure.
    """
    if not AIRTABLE_API_KEY:
        print("No Airtable API key configured")
        return None
    
    try:
        job_data = {
            'fields': {
                'Job Number': job_number,
                'Project Name': job_name,
                'Description': description,
                'Status': 'In Progress',
                'Stage': 'Triage',
                'Project Owner': project_owner,
                'Start Date': date.today().isoformat()
            }
        }
        
        # Add client link if we have the record ID
        if client_record_id:
            job_data['fields']['Client Link'] = [client_record_id]
        
        create_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_PROJECTS_TABLE}"
        response = httpx.post(create_url, headers=_get_headers(), json=job_data, timeout=10.0)
        response.raise_for_status()
        
        new_record = response.json()
        print(f"Created project: {job_number}")
        return new_record.get('id')
        
    except Exception as e:
        print(f"Error creating project in Airtable: {e}")
        return None


def create_update(project_record_id, update_text, update_due=None):
    """Create a new update record in the Updates table.
    
    Used by Update endpoint to log status changes.
    Defaults to 5 working days for due date if not specified.
    """
    if not AIRTABLE_API_KEY:
        print("No Airtable API key configured")
        return False
    
    try:
        # Default to 5 working days if no due date provided
        if not update_due:
            update_due = get_next_working_day(date.today(), 5).isoformat()
        
        update_data = {
            'fields': {
                'Project Link': [project_record_id],
                'Update': update_text,
                'Updated on': date.today().isoformat(),
                'Update due': update_due
            }
        }
        
        create_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_UPDATES_TABLE}"
        response = httpx.post(create_url, headers=_get_headers(), json=update_data, timeout=10.0)
        response.raise_for_status()
        
        print(f"Created update for project {project_record_id}: {update_text}")
        return True
        
    except Exception as e:
        print(f"Error creating update in Airtable: {e}")
        return False


def update_project_fields(job_number, updates):
    """Update specific fields on a Project record.
    
    Used for Stage, Status, Live Date, With Client changes.
    NOT for Update field - that's a lookup from Updates table.
    """
    if not AIRTABLE_API_KEY:
        print("No Airtable API key configured")
        return False
    
    try:
        # First find the record
        project = get_project_by_job_number(job_number)
        
        if not project:
            return False
        
        # Build update payload - only include valid fields
        field_mapping = {
            'Stage': 'Stage',
            'Status': 'Status',
            'Live Date': 'Live Date',
            'With Client?': 'With Client?'
        }
        
        update_fields = {}
        for key, airtable_field in field_mapping.items():
            if key in updates and updates[key] is not None:
                update_fields[airtable_field] = updates[key]
        
        if not update_fields:
            print("No project fields to update")
            return True
        
        update_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_PROJECTS_TABLE}/{project['recordId']}"
        update_data = {'fields': update_fields}
        
        response = httpx.patch(update_url, headers=_get_headers(), json=update_data, timeout=10.0)
        response.raise_for_status()
        
        print(f"Updated project {job_number}: {update_fields}")
        return True
        
    except Exception as e:
        print(f"Error updating project in Airtable: {e}")
        return False


def increment_project_round(job_number):
    """Increment the Round counter on a project.
    
    Used by Work-to-Client when sending deliverables.
    Returns the new round number.
    """
    if not AIRTABLE_API_KEY:
        print("No Airtable API key configured")
        return None
    
    try:
        project = get_project_by_job_number(job_number)
        
        if not project:
            return None
        
        current_round = project.get('round', 0) or 0
        new_round = current_round + 1
        
        update_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_PROJECTS_TABLE}/{project['recordId']}"
        update_data = {'fields': {'Round': new_round}}
        
        response = httpx.patch(update_url, headers=_get_headers(), json=update_data, timeout=10.0)
        response.raise_for_status()
        
        print(f"Incremented round for {job_number}: {new_round}")
        return new_round
        
    except Exception as e:
        print(f"Error incrementing round in Airtable: {e}")
        return None
