"""
Tool for checking calendar availability
"""

from datetime import datetime, timedelta
from app.services.google_calendar import GoogleCalendarService


def check_calendar(date_str: str) -> dict:
    """
    Check available time slots in calendar for a given date.

    Args:
        date_str: Date in format 'YYYY-MM-DD' or description like 'today/tomorrow'

    Returns:
        dict with available slots or error message
    """
    try:
        # Parse date
        if date_str.lower() == "today":
            target_date = datetime.now().date()
        elif date_str.lower() == "tomorrow":
            target_date = (datetime.now() + timedelta(days=1)).date()
        else:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

        # Get available slots from Google Calendar API
        calendar_service = GoogleCalendarService()
        available_slots = calendar_service.get_available_slots(str(target_date))

        return {
            "status": "success",
            "date": str(target_date),
            "available_slots": available_slots,
            "message": f"Available slots on {target_date}: {', '.join(available_slots)}",
        }

    except ValueError:
        return {
            "status": "error",
            "message": "Invalid date format. Please use YYYY-MM-DD or say 'today/tomorrow'",
        }
    except Exception as e:
        return {"status": "error", "message": f"Error checking calendar: {str(e)}"}
