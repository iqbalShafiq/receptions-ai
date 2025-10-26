"""
OpenAI Realtime Agent Service - Using official OpenAI Agents SDK
Provides voice conversation with agent tools integration
"""

import os
from agents.realtime import RealtimeAgent, RealtimeRunner
from agents import function_tool, set_default_openai_key
from app.config import settings
from app.agents.tools.calendar_tool import check_calendar
from app.agents.tools.booking_tool import create_booking
from app.agents.tools.transfer_tool import transfer_call
from app.database import SessionLocal

# Set default API key from environment or settings
api_key = os.getenv("OPENAI_API_KEY") or settings.openai_api_key
if api_key:
    set_default_openai_key(api_key)
else:
    raise ValueError("OPENAI_API_KEY not found in environment or settings")


# Define tools for realtime agent
@function_tool
def calendar_availability(date: str) -> str:
    """Check available time slots in calendar for a given date. Use this to see what times are available."""
    result = check_calendar(date)
    return str(result)


@function_tool
def book_appointment(name: str, phone: str, datetime_str: str, notes: str = "") -> str:
    """Create a booking appointment. Use this when customer wants to book a time. Requires name, phone, and date/time in format YYYY-MM-DD HH:MM."""
    db = SessionLocal()
    try:
        # Use a placeholder user_id - in real scenario would come from context
        result = create_booking(
            db, "voice_user", name, phone, datetime_str, notes or None
        )
        return str(result)
    finally:
        db.close()


@function_tool
def transfer_to_owner(reason: str) -> str:
    """Transfer call to owner. Use this when customer needs to speak with the owner or when something is important/urgent."""
    db = SessionLocal()
    try:
        # Use a placeholder conversation_id - in real scenario would come from context
        result = transfer_call(db, 0, reason)
        return str(result)
    finally:
        db.close()


def create_realtime_agent():
    """
    Create a RealtimeAgent with tools for voice conversation.

    Returns:
        RealtimeAgent configured with calendar, booking, and transfer tools
    """
    agent = RealtimeAgent(
        name="Receptionist AI",
        instructions="""You are a friendly and professional AI Receptionist.
Your main responsibilities are:
- Answer questions about business hours and services
- Create appointments/bookings for customers
- Check schedule availability
- Transfer calls to owner when necessary

## Available Tools:
1. calendar_availability(date: str)
   - Use this to check available time slots for a specific date
   - Parameter: date in YYYY-MM-DD format
   - Example: calendar_availability("2025-01-15")
   - Call this when customer asks about availability or before booking

2. book_appointment(name: str, phone: str, datetime_str: str, notes: str = "")
   - Use this to create a booking appointment
   - Required info: customer name, phone number, date & time
   - Format datetime: YYYY-MM-DD HH:MM
   - Example: book_appointment("John Doe", "08123456789", "2025-01-15 14:00", "regular checkup")
   - Always confirm details before calling this tool

3. transfer_to_owner(reason: str)
   - Use this to transfer the call to the business owner
   - For urgent matters or issues beyond AI capabilities
   - Example: transfer_to_owner("Customer has serious complaint")
   - Use when customer specifically asks to speak with owner or for complex issues

Guidelines:
- When customer wants to book, ask for: name, phone number, and preferred date/time
- Check availability first before confirming booking
- If something cannot be handled by you, transfer to owner
- Keep responses friendly, concise, and helpful
- Use tools appropriately when needed for bookings or checking schedules
- Always confirm information before taking action
        """,
        tools=[calendar_availability, book_appointment, transfer_to_owner],
    )
    return agent


def create_realtime_runner():
    """
    Create and configure a RealtimeRunner for handling voice sessions.

    Returns:
        RealtimeRunner configured with proper audio settings
    """
    agent = create_realtime_agent()

    runner = RealtimeRunner(
        starting_agent=agent,
        config={
            "model_settings": {
                "model_name": "gpt-4o-realtime-preview-2024-10-01",
                "voice": "alloy",
                "modalities": ["audio"],  # Support both text and audio
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "turn_detection": {
                    "type": "server_vad",  # Use server-side Voice Activity Detection
                },
            }
        },
    )

    return runner
