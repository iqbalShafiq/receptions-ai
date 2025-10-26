"""
Pytest configuration and fixtures
"""
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import Conversation, Message, Booking, FAQ, TransferLog


# Use in-memory database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine"""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def test_db_session(test_engine):
    """Create test database session"""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestSessionLocal()

    # Create tables for this test
    Base.metadata.create_all(bind=test_engine)

    yield session

    # Cleanup
    session.close()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def sample_conversation(test_db_session):
    """Create sample conversation"""
    conv = Conversation(user_id="test_user")
    test_db_session.add(conv)
    test_db_session.commit()
    test_db_session.refresh(conv)
    return conv


@pytest.fixture
def sample_messages(test_db_session, sample_conversation):
    """Create sample messages"""
    msg1 = Message(
        conversation_id=sample_conversation.id,
        role="user",
        content="Hello, I want to book an appointment"
    )
    msg2 = Message(
        conversation_id=sample_conversation.id,
        role="assistant",
        content="Sure, what date would you prefer?"
    )
    test_db_session.add_all([msg1, msg2])
    test_db_session.commit()
    return [msg1, msg2]


@pytest.fixture
def sample_faq(test_db_session):
    """Create sample FAQ"""
    faq = FAQ(
        question="What are your hours?",
        answer="We are open Monday-Friday 9AM-5PM",
        category="Hours"
    )
    test_db_session.add(faq)
    test_db_session.commit()
    test_db_session.refresh(faq)
    return faq


@pytest.fixture
def sample_booking(test_db_session):
    """Create sample booking"""
    from datetime import datetime, timedelta

    booking = Booking(
        user_id="test_user",
        user_name="John Doe",
        user_phone="+1234567890",
        datetime=datetime.now() + timedelta(days=1),
        notes="Test booking"
    )
    test_db_session.add(booking)
    test_db_session.commit()
    test_db_session.refresh(booking)
    return booking


# Test markers
def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow tests")
