# Dot Shared Module
# Common functions used across all Dot apps

from .config import (
    AIRTABLE_API_KEY,
    AIRTABLE_BASE_ID,
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    VALID_CLIENT_CODES
)

from .helpers import (
    strip_markdown_json,
    get_next_working_day,
    format_date_display
)

from .airtable import (
    get_project_by_job_number,
    get_client_by_code,
    get_active_jobs_for_client,
    increment_client_job_number,
    create_project,
    create_update,
    update_project_fields,
    increment_project_round
)
