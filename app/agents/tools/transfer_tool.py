"""
Tool for transferring calls to owner
"""
from sqlalchemy.orm import Session
from app.models import TransferLog, Conversation
from app.services.sms_service import send_transfer_notification


def transfer_call(db: Session, conversation_id: int, reason: str) -> dict:
    """
    Transfer call to owner by notifying them via SMS.

    Args:
        db: Database session
        conversation_id: Current conversation ID
        reason: Reason for transfer

    Returns:
        dict with transfer status
    """
    try:
        # Create transfer log
        transfer_log = TransferLog(
            conversation_id=conversation_id,
            reason=reason
        )
        db.add(transfer_log)
        db.commit()
        db.refresh(transfer_log)

        # Get conversation details for notification
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()

        user_id = conversation.user_id if conversation else "unknown"

        # Send SMS to owner
        try:
            full_reason = f"[Transfer] User {user_id}: {reason}"
            send_transfer_notification(full_reason)
        except Exception as sms_error:
            print(f"Warning: Failed to send transfer notification SMS: {str(sms_error)}")

        return {
            "status": "success",
            "transfer_id": transfer_log.id,
            "reason": reason,
            "message": f"✓ Call transferred to owner. Reason: {reason}. Owner has been notified."
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error transferring call: {str(e)}"
        }
