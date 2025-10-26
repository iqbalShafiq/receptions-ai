# Receptionist AI 🤖

AI-powered receptionist system with voice & text support, automated booking, and SMS notifications.

## Features

✅ **Voice & Text Support**
- Real-time voice calls via OpenAI Realtime API
- Text chat via HTTP API
- WebSocket support for both

✅ **Smart Booking**
- Check Google Calendar availability
- Create bookings automatically
- SMS confirmation to customers

✅ **Conversation History**
- All messages saved in SQLite
- Context preserved across messages
- Per-user conversation tracking

✅ **Smart Agent** (LangChain)
- FAQ knowledge base integration
- Automatic tool selection
- Natural language understanding

✅ **Automation**
- SMS reminders 24 hours before booking
- Review request SMS after booking
- Owner notifications for important calls

✅ **Multi-channel**
- Google Calendar integration
- Twilio SMS notifications
- OpenAI Realtime voice

---

## Quick Start

### Prerequisites
- Python 3.10+
- OpenAI API Key
- Google Calendar API credentials (optional)
- Twilio Account (optional)

### Installation

```bash
# Clone/setup project
cd receptionist-ai

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your credentials
```

### Running the Server

```bash
# Option 1: Direct
python -m uvicorn app.main:app --reload

# Option 2: Via script
python app/main.py
```

Server runs on `http://localhost:8000`

---

## API Usage

### 1. Text Chat

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "user123",
    "message": "Saya mau booking appointment besok jam 2"
  }'
```

**Response:**
```json
{
  "response": "Baik! Saya cek jadwal besok jam 2. Nama Anda siapa?",
  "action": "booking"
}
```

### 2. Voice Chat (WebSocket)

```javascript
const ws = new WebSocket('ws://localhost:8000/voice?conversation_id=user123');

ws.onopen = () => {
  // Send text via WebSocket
  ws.send(JSON.stringify({
    type: "text",
    message: "Saya ingin membuat appointment"
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Response:', data);
};
```

### 3. Get Conversation History

```bash
curl http://localhost:8000/conversations/user123
```

### 4. View Bookings

```bash
curl http://localhost:8000/bookings
```

---

## Environment Variables

Create `.env` file with:

```env
# App
DEBUG=True
DATABASE_URL=sqlite:///./receptionist_ai.db

# OpenAI (Required)
OPENAI_API_KEY=sk-your-key-here

# Google Calendar (Optional)
GOOGLE_CALENDAR_CREDENTIALS=path/to/credentials.json
GOOGLE_CALENDAR_ID=your-calendar@gmail.com

# Twilio (Optional)
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=+1234567890
OWNER_PHONE_NUMBER=+1234567890
```

---

## Architecture

### Database Schema
- **conversations** - Chat sessions
- **messages** - Message history
- **bookings** - Booking records
- **faq** - FAQ knowledge base
- **transfer_logs** - Call transfer logs

### Services

**OpenAI Realtime**
- Voice I/O via WebSocket
- Real-time speech processing

**LangChain Agent**
- Conversation understanding
- Tool calling (booking, calendar, transfer)
- FAQ integration

**Google Calendar**
- Check availability
- Create events
- Delete events

**Twilio SMS**
- Send reminders
- Send review requests
- Notify owner

**APScheduler**
- Background job runner
- 5-min reminder checks
- Hourly review request checks

---

## Project Structure

```
receptionist-ai/
├── app/
│   ├── agents/              # LangChain agent + tools
│   ├── api/                 # FastAPI routes
│   ├── models/              # SQLAlchemy models
│   ├── services/            # External services
│   ├── config.py            # Configuration
│   ├── database.py          # Database setup
│   └── main.py              # App entry point
├── .env.example             # Environment template
├── requirements.txt         # Python dependencies
├── CLAUDE.md                # Project overview & architecture
└── README.md                # This file
```

---

## Configuration

### Adding FAQ

FAQ is loaded from database into agent's system prompt at startup.

To add FAQ programmatically:

```python
from app.database import SessionLocal
from app.models import FAQ

db = SessionLocal()
faq = FAQ(
    question="Jam kerja berapa?",
    answer="Kami buka Senin-Jumat 9-5, Sabtu 9-12",
    category="Hours"
)
db.add(faq)
db.commit()
db.close()
```

### Google Calendar Setup

1. Create service account in Google Cloud Console
2. Download JSON credentials
3. Share calendar with service account email
4. Set `GOOGLE_CALENDAR_CREDENTIALS` path in `.env`

### Twilio Setup

1. Create Twilio account
2. Get Account SID, Auth Token, Phone Number
3. Set in `.env` variables

---

## Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=app
```

---

## Production Deployment

```bash
# Production server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Or with Gunicorn
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker
```

---

## Troubleshooting

### Database Issues
```bash
# Reset database
rm receptionist_ai.db
python app/main.py  # Recreates tables
```

### OpenAI API Errors
- Verify API key in `.env`
- Check quota and billing
- Ensure internet connection

### Google Calendar Not Working
- Verify credentials file exists
- Check service account has calendar access
- Verify calendar ID is correct

### SMS Not Sending
- Check Twilio credentials
- Verify phone numbers are in E.164 format
- Check account has SMS balance

---

## Contributing

Feel free to submit issues and enhancement requests!

---

## License

MIT

---

## Support

- 📖 See `CLAUDE.md` for detailed architecture and development guide
- 🔧 Check `.env.example` for configuration options
- 📚 API documentation is included in this README (see "API Usage" section)

---

**Built with ❤️ using FastAPI, LangChain, and OpenAI**
