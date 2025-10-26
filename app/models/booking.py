from sqlalchemy import Column, Integer, String, DateTime, Text, func, Boolean
from app.database import Base


class Booking(Base):
    """Store booking data"""
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), index=True)
    user_name = Column(String(255))
    user_phone = Column(String(20))
    datetime = Column(DateTime, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    google_event_id = Column(String(255), nullable=True)  # Track Google Calendar event ID
    reminder_sent = Column(Boolean, default=False)  # Track if reminder SMS sent
    review_sent = Column(Boolean, default=False)  # Track if review request SMS sent
