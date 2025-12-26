# Dot Shared Config
# Central configuration for all Dot apps

import os

# Airtable
AIRTABLE_API_KEY = os.environ.get('AIRTABLE_API_KEY')
AIRTABLE_BASE_ID = 'app8CI7NAZqhQ4G1Y'

# Table names
AIRTABLE_CLIENTS_TABLE = 'Clients'
AIRTABLE_PROJECTS_TABLE = 'Projects'
AIRTABLE_UPDATES_TABLE = 'Updates'

# Anthropic
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
ANTHROPIC_MODEL = 'claude-sonnet-4-20250514'

# Valid client codes
VALID_CLIENT_CODES = ['ONE', 'ONS', 'SKY', 'TOW', 'FIS', 'FST', 'WKA', 'HUN', 'LAB', 'EON', 'OTH']
