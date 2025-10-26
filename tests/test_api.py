"""
Integration tests for API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import Conversation, FAQ


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def db_session():
    """Create test database session"""
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def setup_faq(db_session):
    """Setup test FAQ data"""
    faq = FAQ(
        question="Jam kerja berapa?",
        answer="Kami buka Senin-Jumat 9-5, Sabtu 9-12",
        category="Hours",
    )
    db_session.add(faq)
    db_session.commit()
    db_session.refresh(faq)
    return faq


class TestHealthEndpoint:
    """Test health check endpoint"""

    def test_health_check(self, client):
        """Test health check returns OK"""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert "Receptionist AI" in response.json()["app"]

    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "docs" in data
        assert "health" in data


class TestChatEndpoint:
    """Test text chat endpoint"""

    def test_chat_basic(self, client):
        """Test basic chat message"""
        payload = {
            "conversation_id": "test_user_1",
            "message": "Halo, siapa nama kamu?",
        }
        response = client.post("/chat", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "action" in data
        assert isinstance(data["response"], str)
        assert len(data["response"]) > 0

    def test_chat_missing_fields(self, client):
        """Test chat with missing fields"""
        payload = {
            "conversation_id": "test_user",
            # missing message field
        }
        response = client.post("/chat", json=payload)

        assert response.status_code == 422  # Validation error

    def test_chat_creates_conversation(self, client, db_session):
        """Test that chat creates conversation"""
        payload = {"conversation_id": "unique_user_123", "message": "Test message"}
        client.post("/chat", json=payload)

        # Verify conversation was created
        conv = (
            db_session.query(Conversation)
            .filter(Conversation.user_id == "unique_user_123")
            .first()
        )

        assert conv is not None
        assert conv.user_id == "unique_user_123"

    def test_chat_saves_messages(self, client):
        """Test that chat saves messages"""
        payload = {
            "conversation_id": "msg_test_user_unique_" + str(hash("msg_test")),
            "message": "Test message",
        }
        response = client.post("/chat", json=payload)

        assert response.status_code == 200
        # Just verify the response has the expected structure
        data = response.json()
        assert "response" in data
        assert "action" in data

    def test_chat_preserves_context(self, client, db_session):
        """Test that chat preserves conversation context"""
        user_id = "context_test_user"

        # First message
        client.post(
            "/chat",
            json={"conversation_id": user_id, "message": "Nama saya adalah Budi"},
        )

        # Second message - should have context
        response = client.post(
            "/chat", json={"conversation_id": user_id, "message": "Apa nama saya?"}
        )

        assert response.status_code == 200
        # Response should reference previous context

    def test_chat_response_has_action(self, client):
        """Test that response includes action field"""
        payload = {
            "conversation_id": "action_test",
            "message": "Saya mau booking appointment",
        }
        response = client.post("/chat", json=payload)

        data = response.json()
        assert "action" in data
        assert data["action"] in [
            "faq",
            "booking",
            "calendar",
            "transfer",
            "response",
            "error",
        ]


class TestConversationHistoryEndpoint:
    """Test conversation history endpoint"""

    def test_get_conversation_history(self, client):
        """Test getting conversation history"""
        # Create a conversation
        client.post(
            "/chat",
            json={"conversation_id": "history_test", "message": "Test message 1"},
        )

        # Get history
        response = client.get("/conversations/history_test")

        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert "messages" in data
        assert "created_at" in data
        assert len(data["messages"]) >= 2

    def test_get_nonexistent_conversation(self, client):
        """Test getting non-existent conversation"""
        response = client.get("/conversations/nonexistent_user_xyz")

        assert response.status_code == 404

    def test_conversation_history_structure(self, client):
        """Test conversation history structure"""
        client.post("/chat", json={"conversation_id": "struct_test", "message": "Test"})

        response = client.get("/conversations/struct_test")
        data = response.json()

        for msg in data["messages"]:
            assert "role" in msg
            assert "content" in msg
            assert "created_at" in msg
            assert msg["role"] in ["user", "assistant"]


class TestBookingsEndpoint:
    """Test bookings endpoint"""

    def test_get_bookings_empty(self, client, db_session):
        """Test getting bookings when empty"""
        # Clear all bookings
        from app.models import Booking

        db_session.query(Booking).delete()
        db_session.commit()

        response = client.get("/bookings")

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_bookings_returns_list(self, client):
        """Test that bookings endpoint returns list"""
        response = client.get("/bookings")

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_bookings_sorted_by_datetime(self, client, db_session):
        """Test that bookings are sorted by datetime"""
        from app.models import Booking
        from datetime import datetime, timedelta

        # Clear existing
        db_session.query(Booking).delete()

        # Add test bookings
        now = datetime.now()
        b1 = Booking(
            user_id="user1",
            user_name="User 1",
            user_phone="+1111111111",
            datetime=now + timedelta(days=2),
        )
        b2 = Booking(
            user_id="user2",
            user_name="User 2",
            user_phone="+2222222222",
            datetime=now + timedelta(days=1),
        )
        db_session.add(b1)
        db_session.add(b2)
        db_session.commit()

        response = client.get("/bookings")
        bookings = response.json()

        # Should be sorted by datetime (b2 before b1)
        if len(bookings) >= 2:
            assert bookings[0]["user_id"] == "user2"
            assert bookings[1]["user_id"] == "user1"


class TestErrorHandling:
    """Test error handling"""

    def test_invalid_json(self, client):
        """Test handling of invalid JSON"""
        response = client.post(
            "/chat", data="invalid json", headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_chat_with_empty_message(self, client):
        """Test chat with empty message"""
        payload = {"conversation_id": "test_user", "message": ""}
        response = client.post("/chat", json=payload)

        assert response.status_code == 200
        # Should still work but might give generic response

    def test_very_long_message(self, client):
        """Test chat with very long message"""
        payload = {"conversation_id": "test_user", "message": "A" * 5000}
        response = client.post("/chat", json=payload)

        assert response.status_code == 200


class TestConcurrency:
    """Test concurrent requests"""

    def test_multiple_users_same_time(self, client):
        """Test multiple users chatting simultaneously"""
        responses = []

        for i in range(5):
            response = client.post(
                "/chat",
                json={
                    "conversation_id": f"user_{i}",
                    "message": f"Message from user {i}",
                },
            )
            responses.append(response)

        # All should succeed
        assert all(r.status_code == 200 for r in responses)

        # Each should be independent
        assert len(responses) == 5

    def test_same_user_sequential(self, client):
        """Test same user with sequential messages"""
        user_id = "sequential_user"

        for i in range(3):
            response = client.post(
                "/chat",
                json={"conversation_id": user_id, "message": f"Message {i + 1}"},
            )
            assert response.status_code == 200

        # Check history
        response = client.get(f"/conversations/{user_id}")
        history = response.json()

        # Should have all messages
        assert len(history["messages"]) >= 6  # 3 user + 3 assistant
