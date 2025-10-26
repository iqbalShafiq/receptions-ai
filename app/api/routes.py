import base64
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Conversation, Message
from app.agents.receptionist_agent import process_message
from agents.realtime import RealtimeUserInputText
from pydantic import BaseModel

router = APIRouter()


class ChatRequest(BaseModel):
    """Request model for /chat endpoint"""

    conversation_id: str
    message: str


class ChatResponse(BaseModel):
    """Response model for /chat endpoint"""

    response: str
    action: str


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Handle text chat input.

    - Load/create conversation
    - Save user message
    - Process with agent (TODO: Phase 3)
    - Return response
    """
    # Get or create conversation
    conversation = (
        db.query(Conversation)
        .filter(Conversation.user_id == request.conversation_id)
        .first()
    )

    if not conversation:
        conversation = Conversation(user_id=request.conversation_id)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # Save user message
    user_message = Message(
        conversation_id=conversation.id, role="user", content=request.message
    )
    db.add(user_message)
    db.commit()

    # Process with LangChain agent
    result = process_message(db, conversation.id, request.message)
    response = result["response"]
    action = result["action"]

    # Save assistant message
    assistant_message = Message(
        conversation_id=conversation.id, role="assistant", content=response
    )
    db.add(assistant_message)
    db.commit()

    return ChatResponse(response=response, action=action)


@router.get("/conversations/{conversation_id}")
def get_conversation_history(conversation_id: str, db: Session = Depends(get_db)):
    """Get conversation history"""
    conversation = (
        db.query(Conversation).filter(Conversation.user_id == conversation_id).first()
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
        .all()
    )

    return {
        "conversation_id": conversation.user_id,
        "created_at": conversation.created_at,
        "messages": [
            {"role": msg.role, "content": msg.content, "created_at": msg.created_at}
            for msg in messages
        ],
    }


@router.get("/bookings")
def get_bookings(db: Session = Depends(get_db)):
    """Get all bookings"""
    from app.models import Booking

    bookings = db.query(Booking).order_by(Booking.datetime).all()
    return bookings


@router.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "ok", "app": "Receptionist AI"}


@router.websocket("/voice")
async def voice_call(websocket: WebSocket, conversation_id: str):
    """
    WebSocket endpoint for voice/text messages with OpenAI Realtime Agent.

    Connection format:
    ws://localhost:8000/voice?conversation_id=user123
    """
    import asyncio
    from app.database import SessionLocal
    from app.services.realtime_agent import create_realtime_runner

    await websocket.accept()

    # Get or create conversation
    db = SessionLocal()
    try:
        conversation = (
            db.query(Conversation)
            .filter(Conversation.user_id == conversation_id)
            .first()
        )

        if not conversation:
            conversation = Conversation(user_id=conversation_id)
            db.add(conversation)
            db.commit()
            db.refresh(conversation)

        conv_db_id = conversation.id

        # Create realtime agent runner with FAQ loaded from database
        runner = create_realtime_runner(db)
    finally:
        db.close()

    try:
        # Run the realtime session
        session = await runner.run()
        print(f"[VOICE] Session created for conversation: {conversation_id}")

        # Send connection confirmation
        await websocket.send_json(
            {
                "type": "connection",
                "status": "connected",
                "conversation_id": conversation_id,
                "openai_connected": True,
            }
        )

        # Use the runner session with async context manager
        async with session:
            # Handle bidirectional communication
            async def client_to_agent():
                """Forward messages from client WebSocket to realtime agent"""
                try:
                    while True:
                        data = await websocket.receive_json()
                        msg_type = data.get("type")

                        if msg_type == "audio":
                            # Forward audio to agent - convert base64 to bytes
                            audio_base64 = data.get("audio")
                            if audio_base64:
                                try:
                                    audio_bytes = base64.b64decode(audio_base64)
                                    # Don't commit manually - let Server VAD auto-detect when user stops speaking
                                    await session.send_audio(audio_bytes)
                                except Exception as e:
                                    print(f"[VOICE] ❌ Error sending audio: {e}")
                                    import traceback
                                    traceback.print_exc()

                        elif msg_type == "text":
                            # Forward text to agent
                            text = data.get("message", "").strip()
                            if text:
                                print(f"[VOICE] Text message: {text}")
                                user_input = RealtimeUserInputText(text=text)
                                await session.send_message(user_input)

                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    print(f"[VOICE] ❌ Error in client_to_agent: {e}")
                    import traceback
                    traceback.print_exc()

            async def agent_to_client():
                """Forward messages from realtime agent to client WebSocket"""
                try:
                    async for event in session:
                        try:
                            event_type = type(event).__name__

                            # Log error events with details
                            if event_type == "RealtimeError":
                                error_obj = getattr(event, 'error', None)
                                print(f"[VOICE] ❌ RealtimeError: {error_obj}")
                                continue

                            # Skip non-audio/non-text events
                            if event_type in ["RealtimeRawModelEvent", "RealtimeHistoryUpdated"]:
                                continue

                            # Send audio chunks to client
                            if hasattr(event, "audio") and event.audio:
                                audio_obj = event.audio
                                audio_bytes = getattr(audio_obj, 'data', None)

                                if audio_bytes:
                                    # Convert bytes to base64 for sending to client
                                    audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                                    await websocket.send_json(
                                        {
                                            "type": "audio_delta",
                                            "audio": audio_base64,
                                        }
                                    )

                            # Send text transcription to client
                            elif hasattr(event, "transcript_delta") and event.transcript_delta:
                                await websocket.send_json(
                                    {
                                        "type": "text_delta",
                                        "text": event.transcript_delta,
                                    }
                                )

                            # Audio response complete
                            elif hasattr(event, "type") and event.type == "audio_end":
                                await websocket.send_json({"type": "response_done"})

                        except Exception as e:
                            print(f"[VOICE] ❌ Error processing event: {e}")
                            import traceback
                            traceback.print_exc()

                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    print(f"[VOICE] ❌ Error in agent_to_client: {e}")
                    import traceback
                    traceback.print_exc()

            # Run both directions concurrently
            try:
                await asyncio.gather(
                    client_to_agent(),
                    agent_to_client(),
                )
            except Exception as e:
                pass

    except WebSocketDisconnect:
        pass
    except Exception as e:
        import traceback
        print(f"[VOICE] ❌ Error in voice_call: {e}")
        traceback.print_exc()
        try:
            await websocket.send_json(
                {"type": "error", "message": f"Error: {str(e)}"}
            )
        except:
            pass
