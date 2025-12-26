# Dot Update
# Status updates for Hunch agency jobs

import sys
import os

# Add parent directory to path for shared imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify
from anthropic import Anthropic
import httpx
import json

from shared import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    strip_markdown_json,
    get_project_by_job_number,
    create_update,
    update_project_fields
)

app = Flask(__name__)

# Anthropic client
anthropic_client = Anthropic(
    api_key=ANTHROPIC_API_KEY,
    http_client=httpx.Client(timeout=60.0, follow_redirects=True)
)

# Load prompt
PROMPT_PATH = os.path.join(os.path.dirname(__file__), 'prompt.txt')
with open(PROMPT_PATH, 'r') as f:
    UPDATE_PROMPT = f.read()


@app.route('/update', methods=['POST'])
def update():
    """Process job updates.
    
    Accepts:
        - jobNumber: The job to update
        - emailContent: The update message/email
    
    Returns:
        - teamsPost: Formatted message for Teams
        - airtableUpdate: What was written to Updates table
        - updateCreated: Boolean success flag
        - projectUpdated: Boolean if project fields changed
    """
    try:
        data = request.get_json()
        
        job_number = data.get('jobNumber')
        email_content = data.get('emailContent', '')
        
        if not job_number:
            return jsonify({'error': 'No job number provided'}), 400
        
        if not email_content:
            return jsonify({'error': 'No email content provided'}), 400
        
        # Get project details from Airtable
        project = get_project_by_job_number(job_number)
        
        if not project:
            return jsonify({
                'error': 'job_not_found',
                'jobNumber': job_number,
                'message': f"Could not find job {job_number} in the system"
            }), 404
        
        # Build content for Claude
        update_content = f"""Job Number: {job_number}
Client Name: {project['clientName']}
Current Stage: {project['stage']}
Email/Message Content:
{email_content}"""
        
        # Call Claude for update analysis
        response = anthropic_client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1500,
            temperature=0.2,
            system=UPDATE_PROMPT,
            messages=[
                {'role': 'user', 'content': update_content}
            ]
        )
        
        # Parse response
        content = response.content[0].text
        content = strip_markdown_json(content)
        analysis = json.loads(content)
        
        # Check for errors from Claude
        if analysis.get('error'):
            return jsonify(analysis), 400
        
        # Get the update text
        update_text = analysis.get('airtableUpdate', '')
        
        # Get due date from analysis (or let create_update default to 5 working days)
        update_due = None
        if analysis.get('projectUpdates', {}).get('Update due'):
            update_due = analysis['projectUpdates']['Update due']
        
        # Create the update record in Updates table
        update_created = False
        if update_text:
            update_created = create_update(
                project_record_id=project['recordId'],
                update_text=update_text,
                update_due=update_due
            )
        
        # Update Project fields if needed (Stage, Status, Live Date, With Client)
        project_updated = False
        if analysis.get('projectUpdates'):
            # Remove Update and Update due - those go to Updates table
            project_fields = {k: v for k, v in analysis['projectUpdates'].items() 
                           if k not in ['Update', 'Update due']}
            if project_fields:
                project_updated = update_project_fields(job_number, project_fields)
        
        # Add results to response
        analysis['updateCreated'] = update_created
        analysis['projectUpdated'] = project_updated
        analysis['teamsChannelId'] = project['teamsChannelId']
        analysis['projectRecordId'] = project['recordId']
        
        return jsonify(analysis)
        
    except json.JSONDecodeError as e:
        return jsonify({
            'error': 'Claude returned invalid JSON',
            'details': str(e),
            'raw_response': content if 'content' in locals() else 'No response'
        }), 500
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Dot Update',
        'version': '2.0'
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
