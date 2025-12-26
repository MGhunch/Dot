# Dot Triage
# New job setup for Hunch agency

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
    increment_client_job_number,
    create_project
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
    TRIAGE_PROMPT = f.read()


@app.route('/triage', methods=['POST'])
def triage():
    """Process new job triage.
    
    Accepts:
        - emailContent: The brief/request content
    
    Returns:
        - jobNumber: New job number
        - jobName: Extracted project name
        - All triage analysis fields
        - emailBody: Formatted triage summary HTML
    """
    try:
        data = request.get_json()
        email_content = data.get('emailContent', '')
        
        if not email_content:
            return jsonify({'error': 'No email content provided'}), 400
        
        # Call Claude for triage analysis
        response = anthropic_client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=2000,
            temperature=0.2,
            system=TRIAGE_PROMPT,
            messages=[
                {'role': 'user', 'content': f'Email content:\n\n{email_content}'}
            ]
        )
        
        # Parse response
        content = response.content[0].text
        content = strip_markdown_json(content)
        analysis = json.loads(content)
        
        # Get job number and client info from Airtable
        client_code = analysis.get('clientCode', 'TBC')
        
        if client_code not in ['HUN', 'TBC']:
            job_number, team_id, sharepoint_url, client_record_id = increment_client_job_number(client_code)
        else:
            job_number = f'{client_code} TBC'
            team_id = None
            sharepoint_url = None
            client_record_id = None
        
        # Create job record in Airtable
        job_record_id = None
        if job_number and 'TBC' not in job_number:
            job_record_id = create_project(
                job_number=job_number,
                job_name=analysis.get('jobName', 'Untitled'),
                description=analysis.get('jobSummary', ''),
                project_owner=analysis.get('projectOwner', 'TBC'),
                client_record_id=client_record_id
            )
        
        # Return complete analysis with job info
        return jsonify({
            'jobNumber': job_number,
            'jobName': analysis.get('jobName', 'Untitled'),
            'clientCode': client_code,
            'clientName': analysis.get('clientName', ''),
            'projectOwner': analysis.get('projectOwner', ''),
            'teamId': team_id,
            'sharepointUrl': sharepoint_url,
            'jobRecordId': job_record_id,
            'emailBody': analysis.get('emailBody', ''),
            'fullAnalysis': analysis
        })
        
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
        'service': 'Dot Triage',
        'version': '2.0'
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
