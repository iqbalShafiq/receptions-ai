"""
LangChain Receptionist Agent v1.0
Handles conversation logic, tool calling, and response generation
"""

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from pydantic import SecretStr
from langchain_core.tools import tool
from sqlalchemy.orm import Session
from app.config import settings
from app.models import FAQ, Message, Conversation
from app.agents.tools.calendar_tool import check_calendar
from app.agents.tools.booking_tool import create_booking
from app.agents.tools.transfer_tool import transfer_call


# Define tools for the agent
@tool
def calendar_tool(date: str) -> str:
    """Check available time slots in calendar for a given date. Use this to see what times are available."""
    result = check_calendar(date)
    return str(result)


@tool
def booking_tool(
    user_id: str, user_name: str, user_phone: str, datetime_str: str, notes: str = None
) -> str:
    """Create a booking appointment. Use this when customer wants to book a time. Requires name, phone, and date/time in format YYYY-MM-DD HH:MM."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        result = create_booking(db, user_id, user_name, user_phone, datetime_str, notes)
        return str(result)
    finally:
        db.close()


@tool
def transfer_tool(conversation_id: int, reason: str) -> str:
    """Transfer call to owner. Use this when customer needs to speak with the owner or when something is important/urgent."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        result = transfer_call(db, conversation_id, reason)
        return str(result)
    finally:
        db.close()


def load_faq_to_prompt(db: Session) -> str:
    """Load all FAQ from database and format for system prompt"""
    faqs = db.query(FAQ).all()

    if not faqs:
        return ""

    faq_text = "\n## FAQ Knowledge Base\n"
    for faq in faqs:
        faq_text += f"Q: {faq.question}\nA: {faq.answer}\n\n"

    return faq_text


def create_receptionist_agent(db: Session):
    """
    Create and return a LangChain agent for the receptionist AI.

    Args:
        db: Database session

    Returns:
        Agent instance
    """

    # Load FAQ from database
    faq_context = load_faq_to_prompt(db)

    # System prompt
    system_prompt = f"""Kamu adalah AI Receptionist yang ramah dan profesional.
        Tugas kamu adalah membantu customer dengan:
        - Menjawab pertanyaan dari FAQ knowledge base
        - Membuat appointment/booking
        - Cek jadwal ketersediaan
        - Transfer ke owner jika dirasa penting

        Panduan:
        - Jika customer bertanya, cek FAQ knowledge base di bawah terlebih dahulu
        - Jika customer ingin booking, tanya nama, nomor telepon, dan tanggal/waktu yang diinginkan
        - Jika ada hal yang tidak bisa ditangani, transfer ke owner

        {faq_context}

        Respons kamu harus ramah, singkat, dan membantu. Gunakan tools jika diperlukan.
    """

    # Create LLM
    llm = ChatOpenAI(
        model="gpt-4o-mini", api_key=SecretStr(settings.openai_api_key), temperature=0.7
    )

    # Define tools list
    tools = [calendar_tool, booking_tool, transfer_tool]

    # Create agent using LangChain v1.0 API
    agent = create_agent(llm, tools, system_prompt=system_prompt)

    return agent


def process_message(db: Session, conversation_id: int, user_message: str) -> dict:
    """
    Process user message using the receptionist agent.

    Args:
        db: Database session
        conversation_id: ID of the conversation
        user_message: User's message

    Returns:
        dict with response and action
    """

    try:
        # Create agent
        agent = create_receptionist_agent(db)

        # Load conversation history
        conversation = (
            db.query(Conversation).filter(Conversation.id == conversation_id).first()
        )

        if not conversation:
            return {"response": "Error: Conversation not found", "action": "error"}

        # Load message history for context
        messages = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .all()
        )

        # Build messages list in LangChain v1.0 format
        messages_list = []
        for msg in messages[:-1]:  # Exclude the last message (the current one)
            messages_list.append(
                {
                    "role": "user" if bool(msg.role == "user") else "assistant",
                    "content": msg.content,
                }
            )

        # Run agent with LangChain v1.0 format
        result = agent.invoke(
            {"messages": messages_list + [{"role": "user", "content": user_message}]}
        )

        # Extract response from the last message in the result
        response = result["messages"][-1].content if result.get("messages") else "No response generated"

        # Determine action based on response
        action = "response"
        if "booking" in response.lower() or "appointed" in response.lower():
            action = "booking"
        elif "transfer" in response.lower():
            action = "transfer"
        elif "calendar" in response.lower() or "available" in response.lower():
            action = "calendar"

        return {"response": response, "action": action}

    except Exception as e:
        return {
            "response": f"I encountered an error: {str(e)}. Please try again.",
            "action": "error",
        }
