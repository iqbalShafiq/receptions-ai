"""
SMS Service using Twilio
"""
from app.config import settings
from twilio.rest import Client


class TwilioService:
    """Service to send SMS using Twilio"""

    def __init__(self):
        self.account_sid = settings.twilio_account_sid
        self.auth_token = settings.twilio_auth_token
        self.phone_number = settings.twilio_phone_number
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize Twilio client"""
        try:
            if self.account_sid and self.auth_token:
                self.client = Client(self.account_sid, self.auth_token)
        except Exception as e:
            print(f"Warning: Failed to initialize Twilio: {str(e)}")

    def send_sms(self, to_number: str, message: str) -> dict:
        """
        Send SMS using Twilio.

        Args:
            to_number: Recipient phone number
            message: Message to send

        Returns:
            dict with SMS status
        """
        try:
            if not self.client:
                return {
                    "status": "success",
                    "to": to_number,
                    "message": message,
                    "note": "Twilio not configured - running in test mode"
                }

            sms = self.client.messages.create(
                body=message,
                from_=self.phone_number,
                to=to_number
            )

            return {
                "status": "success",
                "to": to_number,
                "message": message,
                "sid": sms.sid
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error sending SMS: {str(e)}"
            }

    def send_reminder_sms(self, user_phone: str, booking_datetime: str) -> dict:
        """
        Send reminder SMS 24 hours before booking.

        Args:
            user_phone: Customer phone number
            booking_datetime: Booking date and time

        Returns:
            dict with SMS status
        """
        message = f"Reminder: You have a booking scheduled for {booking_datetime}. Please confirm by replying to this message."
        return self.send_sms(user_phone, message)

    def send_review_request_sms(self, user_phone: str, review_link: str = None) -> dict:
        """
        Send review request SMS after service.

        Args:
            user_phone: Customer phone number
            review_link: Google review link

        Returns:
            dict with SMS status
        """
        review_link = review_link or "https://maps.app.goo.gl/review"
        message = f"Thank you for using our service! Please leave a review here: {review_link}"
        return self.send_sms(user_phone, message)

    def send_transfer_notification(self, reason: str) -> dict:
        """
        Send notification to owner about transfer.

        Args:
            reason: Reason for transfer

        Returns:
            dict with SMS status
        """
        message = f"[Call Transfer] {reason}"
        return self.send_sms(settings.owner_phone_number, message)


# Global instance
_twilio_service = None


def get_twilio_service() -> TwilioService:
    """Get or create Twilio service instance"""
    global _twilio_service
    if _twilio_service is None:
        _twilio_service = TwilioService()
    return _twilio_service


def send_sms(to_number: str, message: str) -> dict:
    """Send SMS - convenience function"""
    return get_twilio_service().send_sms(to_number, message)


def send_reminder_sms(user_phone: str, booking_datetime: str) -> dict:
    """Send reminder SMS - convenience function"""
    return get_twilio_service().send_reminder_sms(user_phone, booking_datetime)


def send_review_request_sms(user_phone: str) -> dict:
    """Send review request SMS - convenience function"""
    return get_twilio_service().send_review_request_sms(user_phone)


def send_transfer_notification(reason: str) -> dict:
    """Send transfer notification - convenience function"""
    return get_twilio_service().send_transfer_notification(reason)
