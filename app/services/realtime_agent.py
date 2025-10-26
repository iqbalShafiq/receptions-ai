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
    """Check available time slots in calendar for a given date."""
    result = check_calendar(date)
    return str(result)


@function_tool
def book_appointment(name: str, phone: str, datetime_str: str, notes: str = "") -> str:
    """Create a booking appointment. Format: YYYY-MM-DD HH:MM"""
    db = SessionLocal()
    try:
        # Use a placeholder user_id - in real scenario would come from context
        result = create_booking(db, "voice_user", name, phone, datetime_str, notes or None)
        return str(result)
    finally:
        db.close()


@function_tool
def transfer_to_owner(reason: str) -> str:
    """Transfer call to owner for important matters."""
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
        instructions="""Kamu adalah AI Receptionist yang ramah dan profesional.
Tugas kamu adalah membantu customer dengan:
- Menjawab pertanyaan tentang jam kerja dan layanan
- Membuat appointment/booking
- Cek jadwal ketersediaan
- Transfer ke owner jika dirasa penting

Panduan:
- Jika customer ingin booking, tanya nama, nomor telepon, dan tanggal/waktu yang diinginkan
- Jika ada hal yang tidak bisa ditangani, transfer ke owner
- Respons harus ramah, singkat, dan membantu
- Gunakan tools ketika diperlukan untuk membuat booking atau cek jadwal""",
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
                "modalities": ["text", "audio"],  # Support both text and audio
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "turn_detection": {
                    "type": "server_vad",  # Use server-side Voice Activity Detection
                },
            }
        },
    )

    return runner
