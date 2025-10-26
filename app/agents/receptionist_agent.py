"""
LangChain Receptionist Agent v1.0
Handles conversation logic, tool calling, and response generation
"""

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.callbacks import BaseCallbackHandler
from pydantic import SecretStr
from langchain_core.tools import tool
from sqlalchemy.orm import Session
from app.config import settings
from app.models import FAQ, Message, Conversation
from app.agents.tools.calendar_tool import check_calendar
from app.agents.tools.booking_tool import create_booking
from app.agents.tools.transfer_tool import transfer_call
from typing import Any


# Custom callback for token streaming with real-time yielding
class StreamingTokenCallback(BaseCallbackHandler):
    """Callback to capture and yield tokens as they're generated"""

    def __init__(self):
        self.tokens = []
        self.token_queue = []  # Queue for real-time token streaming

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Called when LLM generates a new token"""
        self.tokens.append(token)
        self.token_queue.append(token)  # Add to queue for streaming

    def get_tokens(self):
        """Get accumulated tokens"""
        return "".join(self.tokens)

    def get_new_tokens(self):
        """Get and clear new tokens from queue"""
        if self.token_queue:
            tokens = "".join(self.token_queue)
            self.token_queue = []
            return tokens
        return ""

    def clear(self):
        """Clear accumulated tokens"""
        self.tokens = []
        self.token_queue = []


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
    system_prompt = f"""You are a friendly and professional AI Receptionist.
        Your main responsibilities are:
        - Answer questions from the FAQ knowledge base
        - Create appointments/bookings for customers
        - Check schedule availability
        - Transfer calls to owner when necessary

        ## Available Tools:
        1. calendar_tool(date: str)
        - Use this to check available time slots for a specific date
        - Parameter: date in YYYY-MM-DD format
        - Example: calendar_tool("2025-01-15")
        - Call this when customer asks about availability or before confirming a booking

        2. booking_tool(user_id: str, user_name: str, user_phone: str, datetime_str: str, notes: str = None)
        - Use this to create a booking appointment
        - Required info: user_id (from conversation), customer name, phone number, date & time
        - Format datetime: YYYY-MM-DD HH:MM
        - Example: booking_tool("user123", "John Doe", "08123456789", "2025-01-15 14:00", "regular checkup")
        - Always collect all required information before calling this tool
        - Confirm details with customer before creating the booking

        3. transfer_tool(conversation_id: int, reason: str)
        - Use this to transfer the call to the business owner
        - Required: conversation_id and clear reason for transfer
        - Example: transfer_tool(1, "Customer has billing complaint that needs owner attention")
        - Use when customer specifically asks to speak with owner or for complex issues beyond your capability

        Guidelines:
        - If customer asks a question, check the FAQ knowledge base below first
        - If customer wants to book, ask for: name, phone number, and preferred date/time
        - Check availability using calendar_tool before confirming bookings
        - If something cannot be handled, use transfer_tool to escalate to owner
        - Keep responses friendly, concise, and helpful
        - Use tools appropriately when needed

        {faq_context}

        Remember: Always verify you have all required information before calling any tool.

        ## Response Format Instructions
        Format ALL your responses using Markdown syntax. When give list, please show as valid markdown table.
    """

    # Create LLM with streaming enabled
    llm = ChatOpenAI(
        model="gpt-4.1-mini",
        api_key=SecretStr(settings.openai_api_key),
        temperature=0.7,
        streaming=True,  # Enable token-level streaming
    )

    # Define tools list
    tools = [calendar_tool, booking_tool, transfer_tool]

    # Create agent using LangChain v1.0 API
    agent = create_agent(llm, tools, system_prompt=system_prompt)

    return agent


def process_message(db: Session, conversation_id: int, user_message: str) -> dict:
    """
    Process user message using the receptionist agent (invoke mode - for backwards compatibility).

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
        response = (
            result["messages"][-1].content
            if result.get("messages")
            else "No response generated"
        )

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


async def process_message_stream_async(db: Session, conversation_id: int, user_message: str):
    """
    Async process user message with real-time token streaming.

    Args:
        db: Database session
        conversation_id: ID of the conversation
        user_message: User's message

    Yields:
        dict with chunk data
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    try:
        # Create agent
        agent = create_receptionist_agent(db)

        # Load conversation history
        conversation = (
            db.query(Conversation).filter(Conversation.id == conversation_id).first()
        )

        if not conversation:
            yield {"type": "error", "data": "Conversation not found"}
            return

        # Load message history
        messages = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .all()
        )

        messages_list = []
        for msg in messages[:-1]:
            messages_list.append(
                {
                    "role": "user" if bool(msg.role == "user") else "assistant",
                    "content": msg.content,
                }
            )

        agent_input = {
            "messages": messages_list + [{"role": "user", "content": user_message}]
        }

        # Setup streaming callback
        token_callback = StreamingTokenCallback()

        # Run agent.invoke() in background thread
        executor = ThreadPoolExecutor(max_workers=1)
        loop = asyncio.get_event_loop()

        # Start agent execution in background
        agent_task = loop.run_in_executor(
            executor,
            lambda: agent.invoke(agent_input, config={"callbacks": [token_callback]})
        )

        # Poll for new tokens while agent is running
        action = "response"
        full_response = ""

        while not agent_task.done():
            # Check for new tokens
            new_tokens = token_callback.get_new_tokens()
            if new_tokens:
                full_response += new_tokens
                yield {"type": "content", "data": new_tokens}

            # Small delay before next poll
            await asyncio.sleep(0.05)

        # Wait for agent to complete
        result = await agent_task

        # Get any remaining tokens
        final_tokens = token_callback.get_new_tokens()
        if final_tokens:
            full_response += final_tokens
            yield {"type": "content", "data": final_tokens}

        # Get full response from result as fallback
        if not full_response:
            full_response = (
                result["messages"][-1].content if result.get("messages") else ""
            )
            if full_response:
                yield {"type": "content", "data": full_response}

        # Determine action
        if full_response:
            if "booking" in full_response.lower() or "appointed" in full_response.lower():
                action = "booking"
            elif "transfer" in full_response.lower():
                action = "transfer"
            elif "calendar" in full_response.lower() or "available" in full_response.lower():
                action = "calendar"

        yield {
            "type": "done",
            "data": {"action": action, "full_response": full_response},
        }

    except Exception as e:
        yield {
            "type": "error",
            "data": f"I encountered an error: {str(e)}. Please try again.",
        }


def process_message_stream(db: Session, conversation_id: int, user_message: str):
    """
    Process user message using the receptionist agent with streaming output.

    Args:
        db: Database session
        conversation_id: ID of the conversation
        user_message: User's message

    Yields:
        dict with chunk data in format: {"type": "content" | "tool_call" | "done", "data": ...}
    """

    try:
        # Create agent
        agent = create_receptionist_agent(db)

        # Load conversation history
        conversation = (
            db.query(Conversation).filter(Conversation.id == conversation_id).first()
        )

        if not conversation:
            yield {"type": "error", "data": "Conversation not found"}
            return

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

        # Build input for agent
        agent_input = {
            "messages": messages_list + [{"role": "user", "content": user_message}]
        }

        # Initialize action variable
        action = "response"
        full_response = ""

        # Setup streaming callback to capture tokens
        token_callback = StreamingTokenCallback()

        # Invoke agent with streaming enabled
        # streaming=True in LLM config + callback will capture tokens as generated
        result = agent.invoke(agent_input, config={"callbacks": [token_callback]})

        # Extract full response from result
        full_response = (
            result["messages"][-1].content if result.get("messages") else ""
        )

        # Stream response with incremental chunks for real-time UI updates
        # This simulates token streaming even if callback didn't capture individual tokens
        if full_response:
            # Stream in variable-sized chunks for more natural typing effect
            # Smaller chunks near punctuation, larger chunks for regular text
            buffer = ""

            for i, char in enumerate(full_response):
                buffer += char

                # Yield on:
                # 1. Every word boundary (space)
                # 2. After punctuation
                # 3. Every ~10 chars to ensure UI responsiveness
                should_yield = (
                    (len(buffer) > 0 and buffer[-1] in " ,.!?:;\n")
                    or len(buffer) >= 10
                    or i == len(full_response) - 1
                )

                if should_yield:
                    yield {"type": "content", "data": buffer}
                    buffer = ""
                    # Note: delay removed from here - let async endpoint handle timing

        # Determine action based on full response
        if full_response:
            if (
                "booking" in full_response.lower()
                or "appointed" in full_response.lower()
            ):
                action = "booking"
            elif "transfer" in full_response.lower():
                action = "transfer"
            elif (
                "calendar" in full_response.lower()
                or "available" in full_response.lower()
            ):
                action = "calendar"

        yield {
            "type": "done",
            "data": {"action": action, "full_response": full_response},
        }

    except Exception as e:
        yield {
            "type": "error",
            "data": f"I encountered an error: {str(e)}. Please try again.",
        }
