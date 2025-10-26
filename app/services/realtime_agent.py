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
from app.models import FAQ
from sqlalchemy.orm import Session

# Set default API key from environment or settings
api_key = os.getenv("OPENAI_API_KEY") or settings.openai_api_key
if api_key:
    set_default_openai_key(api_key)
else:
    raise ValueError("OPENAI_API_KEY not found in environment or settings")


def load_faq_to_prompt(db: Session) -> str:
    """Load all FAQ from database and format for system prompt"""
    faqs = db.query(FAQ).all()

    if not faqs:
        return ""

    faq_text = "\n## FAQ Knowledge Base\n"
    for faq in faqs:
        faq_text += f"Q: {faq.question}\nA: {faq.answer}\n\n"

    return faq_text


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


def create_realtime_agent(db: Session | None = None):
    """
    Create a RealtimeAgent with tools for voice conversation.

    Args:
        db: Database session (optional, for loading FAQ)

    Returns:
        RealtimeAgent configured with calendar, booking, and transfer tools
    """
    # Load FAQ from database if db session provided
    faq_context = ""
    if db:
        faq_context = load_faq_to_prompt(db)

    agent = RealtimeAgent(
        name="Receptionist AI",
        instructions=f"""You are a friendly and professional AI Receptionist.
            Your main responsibilities are:
            - Answer questions from the FAQ knowledge base
            - Create appointments/bookings for customers
            - Check schedule availability
            - Transfer calls to owner when necessary

            ## CRITICAL: Always announce what you're about to do BEFORE calling any tool!

            This creates better user experience during the tool execution delay.
            Speak your announcement first, THEN call the tool, THEN respond with the result.

            Examples of announcements:
            - Before checking calendar: "Alright, let me check the schedule for you..."
            - Before booking: "One moment please, I'll create the booking for you..."
            - Before transfer: "Alright, I'll connect you with our owner..."

            ## Available Tools:

            1. calendar_availability(date: str)
            - Use this to check available time slots for a specific date
            - Parameter: date in YYYY-MM-DD format
            - Example: calendar_availability("2025-01-15")
            - ALWAYS announce first: "Let me check the schedule..."
            - Call this when customer asks about availability or before booking

            2. book_appointment(name: str, phone: str, datetime_str: str, notes: str = "")
            - Use this to create a booking appointment
            - Required info: customer name, phone number, date & time
            - Format datetime: YYYY-MM-DD HH:MM
            - Example: book_appointment("John Doe", "08123456789", "2025-01-15 14:00", "regular checkup")
            - ALWAYS announce first: "One moment, I'll create your booking..."
            - Always confirm details before calling this tool

            3. transfer_to_owner(reason: str)
            - Use this to transfer the call to the business owner
            - For urgent matters or issues beyond AI capabilities
            - Example: transfer_to_owner("Customer has serious complaint")
            - ALWAYS announce first: "Let me connect you with our owner..."
            - Use when customer specifically asks to speak with owner or for complex issues

            ## Guidelines:
            - If customer asks a question, check the FAQ knowledge base below first
            - When customer wants to book, ask for: name, phone number, and preferred date/time
            - Check availability first before confirming booking
            - If something cannot be handled by you, transfer to owner
            - Keep responses friendly, concise, and helpful
            - Match the customer's language (Indonesian or English)
            - Use tools appropriately when needed for bookings or checking schedules
            - Always confirm information before taking action

            {faq_context}

            Remember: ANNOUNCE → CALL TOOL → RESPOND WITH RESULT
            Always verify you have all required information before calling any tool.
        """,
        tools=[calendar_availability, book_appointment, transfer_to_owner],
    )
    return agent


def create_realtime_runner(db: Session | None = None):
    """
    Create and configure a RealtimeRunner for handling voice sessions.

    Args:
        db: Database session (optional, for loading FAQ)

    Returns:
        RealtimeRunner configured with proper audio settings
    """
    agent = create_realtime_agent(db)

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
