# Dot Traffic
# Intelligent routing layer for Hunch's agency workflow

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
    get_active_jobs_for_client
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
    TRAFFIC_PROMPT = f.read()


def extract_client_code_from_job(job_number):
    """Extract client code from job number (e.g., 'ONE 125' -> 'ONE')"""
    if job_number and ' ' in job_number:
        return job_number.split(' ')[0]
    return None


def extract_client_code_from_email(email):
    """Extract likely client code from email domain"""
    domain_mapping = {
        'one.nz': 'ONE',
        'sky.co.nz': 'SKY',
        'tower.co.nz': 'TOW',
        'fisherfunds.co.nz': 'FIS',
        'firestop.co.nz': 'FST',
        'whakarongorau.nz': 'WKA',
        'labour.org.nz': 'LAB',
        'eonfibre.co.nz': 'EON'
    }
    
    if not email:
        return None
    
    email_lower = email.lower()
    for domain, code in domain_mapping.items():
        if domain in email_lower:
            return code
    
    return None


@app.route('/traffic', methods=['POST'])
def traffic():
    """Route incoming emails/messages to the correct handler.
    
    Accepts:
        - emailContent: The email body or Teams message
        - subjectLine: Email subject or channel name
        - senderEmail: Sender's email address
        - senderName: Sender's display name
        - allRecipients: List of TO and CC emails
        - hasAttachments: Boolean
        - attachmentNames: List of filenames
        - source: "email" or "teams" (optional, defaults to "email")
    
    Returns:
        - route: Where to send this (triage, update, wip, etc.)
        - confidence: high, medium, or low
        - jobNumber: Extracted/matched job number (if found)
        - Plus enriched data from Airtable
    """
    try:
        data = request.get_json()
        
        # Required field
        content = data.get('emailContent', '')
        if not content:
            return jsonify({'error': 'No content provided'}), 400
        
        # Optional fields
        subject = data.get('subjectLine', '')
        sender_email = data.get('senderEmail', '')
        sender_name = data.get('senderName', '')
        all_recipients = data.get('allRecipients', [])
        has_attachments = data.get('hasAttachments', False)
        attachment_names = data.get('attachmentNames', [])
        source = data.get('source', 'email')
        
        # Try to identify client from sender email
        likely_client_code = extract_client_code_from_email(sender_email)
        
        # Get active jobs for this client (if identified)
        active_jobs = []
        if likely_client_code:
            active_jobs = get_active_jobs_for_client(likely_client_code)
        
        # Format active jobs for the prompt
        active_jobs_text = ""
        if active_jobs:
            active_jobs_text = "\n".join([
                f"- {job['jobNumber']} - {job['jobName']}: {job['description']}"
                for job in active_jobs
            ])
        else:
            active_jobs_text = "No active jobs found for this client"
        
        # Build content for Claude
        full_content = f"""Source: {source}
Subject: {subject}

From: {sender_name} <{sender_email}>
Recipients: {', '.join(all_recipients) if isinstance(all_recipients, list) else all_recipients}
Has Attachments: {has_attachments}
Attachment Names: {', '.join(attachment_names) if isinstance(attachment_names, list) else attachment_names}

Active jobs for this client:
{active_jobs_text}

Message content:
{content}"""
        
        # Call Claude for routing decision
        response = anthropic_client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1500,
            temperature=0.1,
            system=TRAFFIC_PROMPT,
            messages=[
                {'role': 'user', 'content': full_content}
            ]
        )
        
        # Parse response
        result_text = response.content[0].text
        result_text = strip_markdown_json(result_text)
        routing = json.loads(result_text)
        
        # If high confidence with job number, validate and enrich from Airtable
        if routing.get('confidence') == 'high' and routing.get('jobNumber'):
            project = get_project_by_job_number(routing['jobNumber'])
            
            if project:
                # Enrich with project data
                routing['jobName'] = project['jobName']
                routing['clientName'] = project['clientName']
                routing['currentRound'] = project['round']
                routing['currentStage'] = project['stage']
                routing['withClient'] = project['withClient']
                routing['teamsChannelId'] = project['teamsChannelId']
                routing['projectRecordId'] = project['recordId']
            else:
                # Job number not found - switch to clarify
                routing['route'] = 'clarify'
                routing['confidence'] = 'low'
                routing['reason'] = f"Job {routing['jobNumber']} not found in system"
                routing['clarifyEmail'] = f"""<p>Hi {routing.get('senderName', 'there')},</p>
<p>I couldn't find job <strong>{routing['jobNumber']}</strong> in our system.</p>
<p>Could you double-check the job number? Or reply <strong>TRIAGE</strong> if this is a new job.</p>
<p>Dot</p>"""
        
        # Add source to response
        routing['source'] = source
        
        return jsonify(routing)
        
    except json.JSONDecodeError as e:
        return jsonify({
            'error': 'Claude returned invalid JSON',
            'details': str(e),
            'raw_response': result_text if 'result_text' in locals() else 'No response'
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
        'service': 'Dot Traffic',
        'version': '2.0'
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
