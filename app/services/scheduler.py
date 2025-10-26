"""
APScheduler Service
Handles background tasks like SMS reminders and review requests
"""
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Booking
from app.services.sms_service import send_reminder_sms, send_review_request_sms


class SchedulerService:
    """Service to manage background scheduler tasks"""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self._setup_jobs()

    def _setup_jobs(self):
        """Setup all background jobs"""
        # Check for reminders every 5 minutes
        self.scheduler.add_job(
            self._send_booking_reminders,
            IntervalTrigger(minutes=5),
            id="booking_reminders",
            name="Send booking reminders",
            replace_existing=True
        )

        # Check for review requests every hour
        self.scheduler.add_job(
            self._send_review_requests,
            IntervalTrigger(hours=1),
            id="review_requests",
            name="Send review requests",
            replace_existing=True
        )

    def _send_booking_reminders(self):
        """
        Check for bookings in 24 hours and send reminder SMS.
        This runs every 5 minutes.
        """
        try:
            db = SessionLocal()
            try:
                # Get current time and 24-hour target time
                now = datetime.now()
                reminder_time = now + timedelta(hours=24)
                reminder_window_start = reminder_time - timedelta(minutes=10)
                reminder_window_end = reminder_time + timedelta(minutes=10)

                # Find bookings that need reminders
                bookings = db.query(Booking).filter(
                    Booking.datetime >= reminder_window_start,
                    Booking.datetime <= reminder_window_end,
                    Booking.reminder_sent == False  # Only send once
                ).all()

                for booking in bookings:
                    try:
                        # Send reminder SMS
                        result = send_reminder_sms(
                            booking.user_phone,
                            booking.datetime.strftime('%B %d at %I:%M %p')
                        )

                        if result.get("status") == "success":
                            # Mark reminder as sent
                            booking.reminder_sent = True
                            db.commit()
                            print(f"Reminder sent for booking {booking.id}")

                    except Exception as e:
                        print(f"Error sending reminder for booking {booking.id}: {str(e)}")

            finally:
                db.close()

        except Exception as e:
            print(f"Error in booking reminders job: {str(e)}")

    def _send_review_requests(self):
        """
        Check for past bookings and send review request SMS.
        This runs every hour.
        """
        try:
            db = SessionLocal()
            try:
                # Get past bookings from last 2 days that haven't been reviewed
                now = datetime.now()
                two_days_ago = now - timedelta(days=2)

                bookings = db.query(Booking).filter(
                    Booking.datetime < now,  # Past bookings
                    Booking.datetime >= two_days_ago,  # Last 2 days
                    Booking.review_sent == False  # Not sent yet
                ).all()

                for booking in bookings:
                    try:
                        # Send review request SMS
                        result = send_review_request_sms(booking.user_phone)

                        if result.get("status") == "success":
                            # Mark review request as sent
                            booking.review_sent = True
                            db.commit()
                            print(f"Review request sent for booking {booking.id}")

                    except Exception as e:
                        print(f"Error sending review request for booking {booking.id}: {str(e)}")

            finally:
                db.close()

        except Exception as e:
            print(f"Error in review requests job: {str(e)}")

    def start(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            print("Scheduler started")

    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            print("Scheduler stopped")


# Global scheduler instance
_scheduler_service = None


def get_scheduler() -> SchedulerService:
    """Get or create scheduler instance"""
    global _scheduler_service
    if _scheduler_service is None:
        _scheduler_service = SchedulerService()
    return _scheduler_service


def start_scheduler():
    """Start the background scheduler"""
    scheduler = get_scheduler()
    scheduler.start()


def stop_scheduler():
    """Stop the background scheduler"""
    scheduler = get_scheduler()
    scheduler.stop()
