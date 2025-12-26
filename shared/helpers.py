# Dot Shared Helpers
# Utility functions used across all Dot apps

from datetime import date, timedelta


def strip_markdown_json(content):
    """Strip markdown code blocks from Claude's JSON response"""
    content = content.strip()
    if content.startswith('```'):
        # Remove first line (```json or ```)
        content = content.split('\n', 1)[1] if '\n' in content else content[3:]
    if content.endswith('```'):
        # Remove trailing ```
        content = content.rsplit('```', 1)[0]
    return content.strip()


def get_next_working_day(start_date, days=5):
    """Add working days (skipping weekends) to a date.
    
    Args:
        start_date: The date to start from
        days: Number of working days to add (default 5)
    
    Returns:
        Date object for the target working day
    """
    current = start_date
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:  # Monday = 0, Friday = 4
            added += 1
    return current


def format_date_display(date_str):
    """Format date string to 'D MMM' format (e.g., '5 Jan')
    
    Args:
        date_str: Date string in various formats
    
    Returns:
        Formatted string or original if parsing fails
    """
    if not date_str:
        return ''
    try:
        from datetime import datetime
        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
            try:
                date_obj = datetime.strptime(date_str, fmt)
                return date_obj.strftime('%-d %b')
            except ValueError:
                continue
        return date_str
    except:
        return date_str
