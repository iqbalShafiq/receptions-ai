"""
Google Calendar API Service
Handles calendar operations for booking management
"""
import json
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from app.config import settings


class GoogleCalendarService:
    """Service to interact with Google Calendar API"""

    def __init__(self):
        self.credentials = None
        self.service = None
        self.calendar_id = settings.google_calendar_id
        self._init_service()

    def _init_service(self):
        """Initialize Google Calendar API service"""
        try:
            if not settings.google_calendar_credentials:
                raise ValueError("GOOGLE_CALENDAR_CREDENTIALS not set")

            # Load credentials from file path or JSON string
            creds_path = settings.google_calendar_credentials
            try:
                with open(creds_path, 'r') as f:
                    creds_dict = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                # Try parsing as JSON string
                creds_dict = json.loads(creds_path)

            self.credentials = Credentials.from_service_account_info(
                creds_dict,
                scopes=['https://www.googleapis.com/auth/calendar']
            )

            self.service = build('calendar', 'v3', credentials=self.credentials)

        except Exception as e:
            raise Exception(f"Failed to initialize Google Calendar service: {str(e)}")

    def get_available_slots(self, date_str: str, duration_minutes: int = 30) -> list:
        """
        Get available time slots for a given date.

        Args:
            date_str: Date in format 'YYYY-MM-DD'
            duration_minutes: Duration of each slot in minutes

        Returns:
            List of available time slots
        """
        # Parse date - assume all times are in Asia/Jakarta
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        start_time = datetime.combine(target_date, datetime.min.time()).replace(hour=9)
        end_time = datetime.combine(target_date, datetime.min.time()).replace(hour=17, minute=0)

        # Get events for the day - using RFC3339 format with Z (UTC)
        # Add timezone offset for Indonesia (UTC+7)
        start_iso = datetime.combine(target_date, datetime.min.time()).replace(hour=2).isoformat() + 'Z'  # 9AM Jakarta = 2AM UTC
        end_iso = datetime.combine(target_date, datetime.min.time()).replace(hour=10).isoformat() + 'Z'   # 5PM Jakarta = 10AM UTC next day

        events_result = self.service.events().list(
            calendarId=self.calendar_id,
            timeMin=start_iso,
            timeMax=end_iso,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        # Calculate available slots
        available_slots = []
        current_time = start_time

        for event in events:
            # Parse event times
            event_start_str = event['start'].get('dateTime', event['start'].get('date'))
            event_end_str = event['end'].get('dateTime', event['end'].get('date'))

            # Convert UTC datetime string to local datetime (naive)
            if 'T' in event_start_str:
                event_start = datetime.fromisoformat(event_start_str.replace('Z', '+00:00')).replace(tzinfo=None)
            else:
                event_start = datetime.fromisoformat(event_start_str)

            if 'T' in event_end_str:
                event_end = datetime.fromisoformat(event_end_str.replace('Z', '+00:00')).replace(tzinfo=None)
            else:
                event_end = datetime.fromisoformat(event_end_str)

            # Add available slots before event
            while current_time + timedelta(minutes=duration_minutes) <= event_start:
                slot_end = current_time + timedelta(minutes=duration_minutes)
                available_slots.append(f"{current_time.strftime('%H:%M')} - {slot_end.strftime('%H:%M')}")
                current_time = slot_end

            # Skip to after event
            current_time = max(current_time, event_end)

        # Add remaining slots until 5 PM
        while current_time + timedelta(minutes=duration_minutes) <= end_time:
            slot_end = current_time + timedelta(minutes=duration_minutes)
            available_slots.append(f"{current_time.strftime('%H:%M')} - {slot_end.strftime('%H:%M')}")
            current_time = slot_end

        return available_slots

    def create_event(self, title: str, start_datetime: str, end_datetime: str, description: str = None) -> dict:
        """
        Create event in Google Calendar.

        Args:
            title: Event title
            start_datetime: Start time in format 'YYYY-MM-DD HH:MM'
            end_datetime: End time in format 'YYYY-MM-DD HH:MM'
            description: Event description

        Returns:
            dict with event ID and details
        """
        try:
            # Parse datetimes - format without timezone info (local time in Asia/Jakarta)
            start_dt = datetime.strptime(start_datetime, '%Y-%m-%d %H:%M')
            end_dt = datetime.strptime(end_datetime, '%Y-%m-%d %H:%M')

            # Convert to ISO format without Z suffix (Google will use timeZone field)
            start_iso = start_dt.isoformat()
            end_iso = end_dt.isoformat()

            event = {
                'summary': title,
                'description': description or '',
                'start': {'dateTime': start_iso, 'timeZone': 'Asia/Jakarta'},
                'end': {'dateTime': end_iso, 'timeZone': 'Asia/Jakarta'},
            }

            created_event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event
            ).execute()

            return {
                "status": "success",
                "event_id": created_event.get('id'),
                "title": created_event.get('summary'),
                "start": created_event.get('start', {}).get('dateTime'),
                "end": created_event.get('end', {}).get('dateTime'),
                "calendar_link": created_event.get('htmlLink')
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to create event: {str(e)}"
            }

    def delete_event(self, event_id: str) -> dict:
        """
        Delete event from Google Calendar.

        Args:
            event_id: Google Calendar event ID

        Returns:
            dict with status
        """
        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()

            return {"status": "success", "event_id": event_id}

        except Exception as e:
            return {"status": "error", "message": str(e)}

