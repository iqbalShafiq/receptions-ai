"""
Tool for creating bookings
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import Booking
from app.services.google_calendar import GoogleCalendarService
from app.services.sms_service import send_sms


def create_booking(
    db: Session,
    user_id: str,
    user_name: str,
    user_phone: str,
    datetime_str: str,
    notes: str | None = None
) -> dict:
    """
    Create a booking in database and add to Google Calendar.

    Args:
        db: Database session
        user_id: User ID
        user_name: Customer name
        user_phone: Customer phone number
        datetime_str: Booking date/time in format 'YYYY-MM-DD HH:MM'
        notes: Optional notes about the booking

    Returns:
        dict with booking details or error message
    """
    try:
        # Parse datetime
        booking_datetime = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')

        # Validate booking is in future
        if booking_datetime < datetime.now():
            return {
                "status": "error",
                "message": "Cannot book in the past. Please choose a future date."
            }

        # Create booking in database
        booking = Booking(
            user_id=user_id,
            user_name=user_name,
            user_phone=user_phone,
            datetime=booking_datetime,
            notes=notes
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)

        # Add to Google Calendar
        try:
            gc_service = GoogleCalendarService()
            end_datetime = booking_datetime + timedelta(minutes=30)

            cal_result = gc_service.create_event(
                title=f"Booking - {user_name}",
                start_datetime=booking_datetime.strftime('%Y-%m-%d %H:%M'),
                end_datetime=end_datetime.strftime('%Y-%m-%d %H:%M'),
                description=f"Phone: {user_phone}\nNotes: {notes or 'N/A'}"
            )

            if cal_result.get("status") == "success":
                booking.google_event_id = cal_result.get("event_id")
                db.commit()
        except Exception as e:
            print(f"Warning: Failed to add to Google Calendar: {str(e)}")

        # Send confirmation SMS
        try:
            sms_message = f"Booking confirmed! Your appointment is on {booking_datetime.strftime('%B %d at %I:%M %p')}. Reply to confirm."
            send_sms(user_phone, sms_message)
        except Exception as e:
            print(f"Warning: Failed to send SMS: {str(e)}")

        return {
            "status": "success",
            "booking_id": booking.id,
            "customer_name": user_name,
            "customer_phone": user_phone,
            "booking_datetime": str(booking_datetime),
            "notes": notes,
            "message": f"✓ Booking confirmed for {user_name} on {booking_datetime.strftime('%Y-%m-%d at %H:%M')}. Confirmation SMS sent."
        }

    except ValueError:
        return {
            "status": "error",
            "message": "Invalid date/time format. Please use 'YYYY-MM-DD HH:MM'"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error creating booking: {str(e)}"
        }
