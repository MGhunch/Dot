# Dot Work-to-Client
# Handles deliverables being sent to clients

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
    increment_project_round,
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
    WORK_TO_CLIENT_PROMPT = f.read()


@app.route('/work-to-client', methods=['POST'])
def work_to_client():
    """Process deliverables being sent to client.
    
    Accepts:
        - jobNumber: The job this relates to
        - emailContent: The email content
        - attachmentNames: List of files being sent
        - externalRecipient: Client email address
    
    Returns:
        - newRound: The incremented round number
        - folderPath: SharePoint folder path for filing
        - teamsPost: Message to post in Teams
        - chargeableFlag: True if Round 3+
    """
    try:
        data = request.get_json()
        
        job_number = data.get('jobNumber')
        email_content = data.get('emailContent', '')
        attachment_names = data.get('attachmentNames', [])
        external_recipient = data.get('externalRecipient', '')
        
        if not job_number:
            return jsonify({'error': 'No job number provided'}), 400
        
        # Get project details from Airtable
        project = get_project_by_job_number(job_number)
        
        if not project:
            return jsonify({
                'error': 'job_not_found',
                'jobNumber': job_number,
                'message': f"Could not find job {job_number} in the system"
            }), 404
        
        # Increment the round counter
        new_round = increment_project_round(job_number)
        
        if new_round is None:
            new_round = 1  # Fallback if increment failed
        
        # Check if this is a chargeable round (Round 3+)
        chargeable_flag = new_round >= 3
        
        # Generate folder path for SharePoint
        folder_path = f"/{job_number}/Round {new_round}/"
        
        # Build content for Claude to generate update text
        wtc_content = f"""Job Number: {job_number}
Job Name: {project['jobName']}
Client Name: {project['clientName']}
Round: {new_round}
Files sent: {', '.join(attachment_names) if attachment_names else 'Not specified'}
Sent to: {external_recipient}
Email content:
{email_content}"""
        
        # Call Claude to generate update summary
        response = anthropic_client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1000,
            temperature=0.2,
            system=WORK_TO_CLIENT_PROMPT,
            messages=[
                {'role': 'user', 'content': wtc_content}
            ]
        )
        
        # Parse response
        content = response.content[0].text
        content = strip_markdown_json(content)
        analysis = json.loads(content)
        
        # Create update record
        update_text = analysis.get('updateText', f"Round {new_round} sent to client")
        update_created = create_update(
            project_record_id=project['recordId'],
            update_text=update_text
        )
        
        # Update project - set With Client to true
        update_project_fields(job_number, {'With Client?': True})
        
        # Build Teams post
        teams_post = f"SENT TO CLIENT | Round {new_round}"
        if chargeable_flag:
            teams_post += " ⚠️ Additional round - confirm chargeability"
        
        return jsonify({
            'jobNumber': job_number,
            'jobName': project['jobName'],
            'clientName': project['clientName'],
            'newRound': new_round,
            'folderPath': folder_path,
            'teamsPost': teams_post,
            'chargeableFlag': chargeable_flag,
            'updateText': update_text,
            'updateCreated': update_created,
            'teamsChannelId': project['teamsChannelId'],
            'projectRecordId': project['recordId']
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
        'service': 'Dot Work-to-Client',
        'version': '2.0'
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
