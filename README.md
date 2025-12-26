# Dot - Hunch Agency Workflow AI

Dot is the AI-powered workflow assistant for Hunch creative agency. 

## Architecture

```
/dot
├── /shared          # Common code used by all apps
│   ├── config.py    # Environment variables, constants
│   ├── helpers.py   # Utility functions
│   └── airtable.py  # All Airtable operations
│
├── /traffic         # Email/Teams routing
├── /triage          # New job setup
├── /update          # Status updates
├── /wip             # Work In Progress reports
├── /work-to-client  # Deliverable dispatch
├── /feedback        # Client feedback processing
└── /tracker         # Finance reports
```

## Apps

| App | Purpose | Endpoint |
|-----|---------|----------|
| Traffic | Routes incoming requests | `/traffic` |
| Triage | Creates new jobs | `/triage` |
| Update | Logs status changes | `/update` |
| WIP | Generates WIP reports | `/wip` |
| Work-to-Client | Handles deliverables | `/work-to-client` |
| Feedback | Processes client feedback | `/feedback` |
| Tracker | Finance reporting | `/tracker` |

## Deployment

Each app deploys as a separate Railway service from this monorepo.

### Environment Variables

All apps need:
- `ANTHROPIC_API_KEY`
- `AIRTABLE_API_KEY`

### Railway Setup

For each service, set the root directory to the app folder (e.g., `/traffic`).

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (example: traffic)
cd traffic
python app.py
```

## Prompts

Each app has its own `prompt.txt` containing the Claude prompt for that function.
