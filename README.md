# vAIdya - AI-Powered Medical Audio Assistant

**Cyfuture AI Hackathon 1.0 Submission**

> Transform patient audio consultations into structured medical notes with AI-powered transcription, symptom extraction, and diagnostic suggestions.

---

## 🚀 What's New - Major Improvements

This project has been completely refactored with production-ready features:

### ✅ Backend Enhancements
- **Authentication System** - JWT-based user authentication with secure password hashing
- **Database Integration** - SQLAlchemy ORM with user and patient models
- **Refactored NLP Pipeline** - Direct Python imports (removed subprocess calls)
- **CORS Support** - Production-ready cross-origin resource sharing
- **File Validation** - Size limits and format checking
- **Logging System** - Structured logging with file rotation
- **Configuration Management** - Environment-based settings with `.env` support
- **API Versioning** - `/api/v1/...` endpoints for future compatibility

### ✅ Frontend Improvements
- **Audio Recording** - Browser-based recording using MediaRecorder API
- **Modern UI Design** - Gradient backgrounds, glassmorphism, smooth animations
- **Loading States** - Visual feedback during processing
- **Symptom Display** - Color-coded affirmed/negated symptoms
- **Responsive Design** - Mobile-friendly interface

### ✅ DevOps
- **Docker Support** - Containerization with docker-compose
- **Easy Setup** - One-command installation and startup
- **Python 3.12 Compatible** - Updated dependencies for latest Python

---

## 📋 Features

### Core Functionality
- 🎤 **Audio Recording** - Record patient consultations directly in browser
- 📁 **File Upload** - Support for .m4a, .wav, .mp3, .ogg formats
- 🤖 **AI Transcription** - Faster-Whisper for accurate speech-to-text
- 💊 **Symptom Extraction** - Automatic detection with negation handling
- 📝 **Patient Info Extraction** - 10 structured fields (name, age, gender, complaints, history, etc.)
- 📄 **PDF Export** - Generate downloadable patient notes
- 🔐 **User Authentication** - Secure login and registration
- 💾 **Patient History** - Database storage of all consultations

### Technical Features
- **Real-time Processing** - Live audio transcription
- **Multi-user Support** - Unique file naming with UUIDs
- **Error Handling** - Comprehensive error messages
- **Health Checks** - API monitoring endpoint
- **Auto-reload** - Development mode with hot reload

---

## 🛠️ Tech Stack

### Backend
- **Python 3.12** - Core language
- **FastAPI** - Modern web framework
- **PyTorch 2.10** - Deep learning (CPU)
- **Transformers** - Hugging Face NLP models
- **spaCy 3.8** - Industrial NLP with en_core_web_sm
- **Faster-Whisper** - Audio transcription
- **SQLAlchemy** - Database ORM
- **JWT** - Authentication tokens

### Frontend
- **Vanilla JavaScript** - No framework dependencies
- **HTML5/CSS3** - Modern web standards
- **MediaRecorder API** - Audio recording
- **Fetch API** - HTTP requests

### ML Models
- **DistilBERT** - Question answering for patient info
- **NegSpacy** - Medical negation detection
- **Faster-Whisper** - Speech recognition

### Infrastructure
- **Docker** - Containerization
- **SQLite** - Default database (PostgreSQL ready)
- **Uvicorn** - ASGI server
- **ffmpeg** - Audio processing

---

## 📦 Installation

### Prerequisites
- Python 3.8+ (3.12 recommended)
- ffmpeg
- 4GB+ RAM for ML models

### Quick Start

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/vAIdya.git
cd vAIdya
```

2. **Install ffmpeg**

**Windows (using winget):**
```powershell
winget install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt-get install ffmpeg
```

3. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

4. **Download spaCy model**
```bash
pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl
```

5. **Configure environment**
```bash
cp .env.example .env
# Edit .env if needed (defaults work for local development)
```

6. **Run the application**
```bash
python run.py
```

Access at: **http://localhost:8000**

---

## 🐳 Docker Deployment

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## 📚 API Documentation

Once running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Key Endpoints

#### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login and get JWT token
- `GET /api/v1/auth/me` - Get current user info

#### Audio Processing
- `POST /api/v1/upload-audio` - Upload and process audio (requires auth)
- `GET /api/v1/patients` - List all patients
- `GET /api/v1/patients/{id}` - Get patient details

#### Health
- `GET /api/v1/health` - Health check

---

## 🎯 Usage

### 1. Register/Login
```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"doctor1","email":"doctor@test.com","password":"secure123"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -F "username=doctor1" \
  -F "password=secure123"
```

### 2. Upload Audio
```bash
# Use token from login
curl -X POST http://localhost:8000/api/v1/upload-audio \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@audio/consultation.m4a"
```

### 3. View Results
Open http://localhost:8000 in browser:
- Record audio or upload file
- Click "Process Audio"
- View extracted patient info and symptoms
- Access doctor's notes page for editing

---

## 📁 Project Structure

```
vAIdya/
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── logger.py            # Logging utilities
│   ├── database.py          # Database connection
│   ├── models.py            # SQLAlchemy models
│   ├── auth.py              # JWT authentication
│   └── nlp_processor.py     # ML pipeline
├── frontend/
│   ├── index.html           # Main page
│   ├── doctor_notes.html    # Notes editor
│   ├── scripts/
│   │   ├── index.js         # Main logic + recording
│   │   └── doctor_notes.js  # Notes editor logic
│   └── style/
│       ├── index.css        # Main styles
│       └── doctor_notes.css # Notes styles
├── NLP/                     # Legacy scripts (reference)
├── audio/                   # Audio files storage
├── transcripts/             # Processed transcripts
├── requirements.txt         # Python dependencies
├── .env.example             # Environment template
├── .gitignore              # Git exclusions
├── Dockerfile              # Container definition
├── docker-compose.yml      # Docker orchestration
├── run.py                  # Startup script
└── README.md               # This file
```

---

## 🔧 Configuration

Edit `.env` file:

```env
# Application
APP_NAME=vAIdya
DEBUG=True
ENVIRONMENT=development

# Server
HOST=0.0.0.0
PORT=8000

# Security
SECRET_KEY=your-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000

# File Upload
MAX_UPLOAD_SIZE_MB=50
ALLOWED_AUDIO_FORMATS=.m4a,.wav,.mp3,.ogg

# ML Models
WHISPER_MODEL=Systran/faster-distil-whisper-large-v2
WHISPER_DEVICE=cpu
AUDIO_CHUNK_LENGTH_SECONDS=20

# Database
DATABASE_URL=sqlite:///./vaidya.db
```

---

## 🎨 Features in Detail

### Audio Transcription
- Chunks audio into 20-second segments
- Uses Faster-Whisper (optimized OpenAI Whisper)
- Supports multiple audio formats
- Automatic format conversion

### Symptom Extraction
- Medical term recognition with spaCy
- Negation detection (e.g., "no fever" vs "fever")
- Categorized symptom mapping
- Affirmed/negated symptom lists

### Patient Information Extraction
Automatically extracts:
- Patient Name
- Age
- Gender
- Chief Complaint
- Past Medical History
- Family History
- Previous Surgeries
- Lifestyle
- Allergies
- Current Medications

### Security
- Bcrypt password hashing
- JWT token authentication
- CORS protection
- File size/type validation
- SQL injection prevention (ORM)

---

## 🚧 Roadmap

### Completed ✅
- [x] Audio recording and upload
- [x] AI transcription
- [x] Symptom extraction
- [x] Patient info extraction
- [x] User authentication
- [x] Database integration
- [x] Docker support
- [x] Modern UI/UX

### In Progress 🔄
- [ ] Async processing with Celery
- [ ] WebSocket for real-time updates
- [ ] Patient search and filtering

### Planned 📋
- [ ] Diagnostic suggestions
- [ ] Prescription scanning (OCR)
- [ ] Medication database
- [ ] Appointment booking
- [ ] Chatbot assistant
- [ ] Multi-language support
- [ ] Mobile app
- [ ] EHR integration

---

## 🐛 Troubleshooting

### Common Issues

**1. ffmpeg not found**
```bash
# Verify installation
ffmpeg -version

# Restart terminal after installing
```

**2. spaCy model error**
```bash
# Install model directly
pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl
```

**3. Port already in use**
```bash
# Use different port
python run.py  # Edit run.py to change port
```

**4. Slow first processing**
- Normal! ML models load on first run (~1-2 minutes)
- Subsequent runs are much faster

---

## 📊 Performance

- **Transcription:** ~2-3 minutes for 5-minute audio
- **Symptom Extraction:** <1 second
- **Patient Info Extraction:** ~2-3 seconds
- **Total Processing:** ~3-5 minutes (first run), ~1-2 minutes (cached)

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

## 👥 Authors

- **Your Name** - Initial work and improvements

---

## 🙏 Acknowledgments

- OpenAI Whisper for speech recognition
- Hugging Face for transformer models
- spaCy for NLP capabilities
- FastAPI for the excellent web framework
- Cyfuture AI Hackathon for the opportunity

---

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Email: your.email@example.com

---

**Built with ❤️ for better healthcare**
#   v A I d y a  
 